# C32 attention with ex/prob kept in registers (same operand-swap trick as the folded FFN).
# Scores: wmma(K_frag, Q_frag) gives D^T -> each lane holds one query row with 8 consecutive keys; that is the A-fragment
# layout the row-sum WMMA and the AV WMMA want, so scratch.ex (64 ds_store_b16 + reads) and prob (32 ds_store_b8 + reads)
# never touch LDS. Row sums: wmma(ones, ex_frag) yields the lane's own row sum directly. K and V stay in LDS (cross-wave).
#   _pair1: register ex/prob, all four ATTN_SYNC kept
#   _pair2: syncs after scores / after prob removed; the two around the AV->packed write become wave-local fences
#   _pair3: like pair2 but the sync before the projection stays a full sync_window
from pathlib import Path
import re
here=Path(__file__).resolve().parent; root=here.parents[3]; out=Path('/tmp/c32-register-attention'); out.mkdir(exist_ok=True)
s=(root/'hip/c32_fused_ffn_attention.hip').read_text()
a=s.index('template<bool HalfOutput,bool Mapped=false'); b=s.index('\nKERNEL ',a); body=s[a:b]
start_anchor='#if HIP_C32_ABLATE!=2\n _Pragma("unroll 4") for(uint key=0;key<64;key+=16){f8 acc{};'
end_anchor='   acc=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,acc);}av[ci]=acc;\n }\n#endif\n'
assert body.count(start_anchor)==1 and body.count(end_anchor)==1
i0=body.index(start_anchor); i1=body.index(end_anchor)+len(end_anchor)
old_region=body[i0:i1]
assert old_region.count('ATTN_SYNC();')==3  # two on the LOCAL_ATTN_SYNC=0 path plus one inside the LOCAL_ATTN_SYNC=1 branch
tail_old=''' ATTN_SYNC();
 for(uint ci=0;ci<2;ci++)for(uint e=0;e<8;e++)packed[(first+gr()*8+e)*36+ci*16+rc()]=static_cast<unsigned char>(fp8(av[ci][e]));
 ATTN_SYNC();
'''
assert body.count(tail_old)==1 and body.index(tail_old)>=i1
def region(sync1,sync2):
    return '''#if HIP_C32_ABLATE!=2
 h8 exfrag[4];
 _Pragma("unroll 4") for(uint key=0;key<64;key+=16){f8 acc{};
  for(uint kt=0;kt<2;kt++){i2 a{},b{};uint k=kt*16+gr()*8;a=load8(packed+(first+rc())*36+k);b=load8(packed+(64+key+rc())*36+k);acc=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(b,a,acc);}
  h8 ex{};_Pragma("unroll 8") for(uint e=0;e<8;e++){uint q=first+rc(),k=key+gr()*8+e;float score=acc[e]+w[4096+q*64+k],affine=clampf(score*.044921875f+1.30078125f,1.03125f,1.5693359375f);uint ah=(bits(affine)>>13)-0x1c000u;ushort hb=static_cast<ushort>(((ah<<5)+0x8000u)&65535u);ex[e]=__builtin_bit_cast(_Float16,hb);}
  exfrag[key/16]=ex;
 }
'''+sync1+''' i2 pfrag[4];
 {f8 sum{};h8 ones{};for(uint e=0;e<8;e++)ones[e]=(_Float16)1.f;
  _Pragma("unroll 4") for(uint kt=0;kt<4;kt++)sum=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(ones,exfrag[kt],sum);
  _Pragma("unroll 4") for(uint kt=0;kt<4;kt++){i2 p{};_Pragma("unroll 8") for(uint e=0;e<8;e++){float v=float(exfrag[kt][e])*norm_inverse(sum[e]);put_bits(p,e,fp8(v));}pfrag[kt]=p;}
 }
'''+sync2+''' for(uint ci=0;ci<2;ci++){f8 acc{};uint col=ci*16;
  _Pragma("unroll 4") for(uint kt=0;kt<4;kt++){i2 b{};
   for(uint e=0;e<8;e++){uint k=kt*16+gr()*8+e;put_bits(b,e,packed[(128+k)*36+col+rc()]);}
   acc=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(pfrag[kt],b,acc);}av[ci]=acc;
 }
#endif
'''
local=' WG_FENCE(3);WG_FENCE(2);\n'
variants={1:(region(' ATTN_SYNC();\n',' ATTN_SYNC();\n'),tail_old),
          2:(region('',''),tail_old.replace(' ATTN_SYNC();\n',local)),
          3:(region('',''),tail_old.replace(' ATTN_SYNC();\n',local,1))}
code='#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_C32_DIAG_WEIGHTS 1\n'+s
names=re.findall(r'^void (c32_\w+)\(',s[b:],re.M)
for mode,(reg,tail) in variants.items():
    v=body[:i0]+reg+body[i1:]
    j=v.index(tail_old); v=v[:j]+tail+v[j+len(tail_old):]
    v=v.replace('c32_fused_body(',f'c32_rattn{mode}_body(',1)
    code+='\n'+v+'\n'
    for name in names:
        line=next(x for x in s[b:].splitlines() if x.startswith('void '+name+'('))
        code+='KERNEL __attribute__((amdgpu_flat_work_group_size(128,128))) C32_OCC\n'+line.replace('void '+name+'(',f'void {name}_pair{mode}(',1).replace('c32_fused_body<',f'c32_rattn{mode}_body<')+'\n'
(out/'kernel.hip').write_text(code); print('kernels',len(names),'variants',list(variants))
