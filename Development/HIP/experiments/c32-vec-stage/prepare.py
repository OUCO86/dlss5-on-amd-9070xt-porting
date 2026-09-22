# Vectorised f32-row staging for the Mapped (non-RawMapped) C32 kernels: mapped (block start) and post_merge_head.
# Each token row is 32 f32 = 128 bytes = 8 lanes x 16 bytes; lane l stages channels (l&7)*4..+3 of tokens (l>>3)+4k,
# k=0..3: four global_load_b128 per lane instead of sixteen b32, one dword LDS store per token instead of four byte
# stores, two dword in16 stores instead of four b16. Merge (post) also loads the 4 skip bytes as one b32.
# Per-element arithmetic unchanged (bit-exact by construction). Base = production with HIP_C32_BYTE_CHAIN.
#   _pair1: vectorised f32 staging; _pair2/_pair3: identical replications
from pathlib import Path
import re
here=Path(__file__).resolve().parent; root=here.parents[3]; out=Path('/tmp/c32-vec-stage'); out.mkdir(exist_ok=True)
s=(root/'hip/c32_fused_ffn_attention.hip').read_text()
a=s.index('template<bool HalfOutput,bool Mapped=false'); b=s.index('\nKERNEL ',a); body=s[a:b]
anchor='''  }else{
#else
  {
#endif
'''
assert body.count(anchor)==1
vec='''  }else if constexpr(Mapped){
   // f32 rows: lane l stages channels (l&7)*4..+3 of tokens (l>>3)+4k with four 128-bit loads; row indices via ds_bpermute.
   const uint c0=(l&7)*4;float sc[4],sh[4];
   if constexpr(Merge){_Pragma("unroll") for(uint e=0;e<4;e++){sc[e]=scales[c0+e];sh[e]=scales[32+c0+e];}}
   _Pragma("unroll") for(uint k=0;k<4;k++){uint tok=k*4+(l>>3);int src=__builtin_amdgcn_ds_bpermute(int(tok*4),mine);uint idx=src>=0?uint(src):0u;
    f4 q;uint hb4=0;
    if constexpr(Merge){int src2=__builtin_amdgcn_ds_bpermute(int(tok*4),mine2);uint idx2=src2>=0?uint(src2):0u;__builtin_memcpy(&q,raw_input+idx2+c0,16);__builtin_memcpy(&hb4,reinterpret_cast<const unsigned char*>(skip)+idx+c0,4);}
    else __builtin_memcpy(&q,raw_input+idx+c0,16);
    float v[4];uint word=0;
    _Pragma("unroll") for(uint e=0;e<4;e++){float c;if constexpr(Merge){float high=__builtin_amdgcn_cvt_f32_fp8(int((hb4>>(8*e))&255u),0);c=Hrtz(Hrtz(q[e]*sc[e])+high*sh[e]);}else c=q[e];v[e]=src>=0?c:0.f;word|=(fp8(v[e])&255u)<<(8*e);}
    __builtin_memcpy(packed+(first+tok)*36+c0,&word,4);
    if constexpr(NeedIn16){_Float16 h[4];_Pragma("unroll") for(uint e=0;e<4;e++)h[e]=(_Float16)v[e];__builtin_memcpy(in16+(first+tok)*34+c0,h,8);}
   }
'''+anchor
v=body.replace(anchor,vec,1)
code='#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_C32_DIAG_WEIGHTS 1\n'+s+'\nusing f4=float __attribute__((ext_vector_type(4)));\n'
names=re.findall(r'^void (c32_\w+)\(',s[b:],re.M)
for mode in (1,2,3):
    code+='\n'+v.replace('c32_fused_body(',f'c32_vs{mode}_body(',1)+'\n'
    for name in names:
        line=next(x for x in s[b:].splitlines() if x.startswith('void '+name+'('))
        code+='KERNEL __attribute__((amdgpu_flat_work_group_size(128,128))) C32_OCC\n'+line.replace('void '+name+'(',f'void {name}_pair{mode}(',1).replace('c32_fused_body<',f'c32_vs{mode}_body<')+'\n'
(out/'kernel.hip').write_text(code); print('kernels',len(names))
