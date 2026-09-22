# Register-resident ex/prob for the mh_fused c64/c128/c256 attention-project bodies.
# Same operand-swap trick as C32: scores WMMA with (K,Q) yields each lane's query row with 8 consecutive keys = the A
# fragment for the row-sum WMMA and the AV WMMA. all_ex disappears (c256: LDS 59.6 KB -> 25.8 KB, two groups per CU).
# The syncs after scores / after pv / after prob write / after AV go (nothing cross-wave between them); the V-staging
# sync and the end-of-batch sync stay. Per-element arithmetic unchanged. Module set pair1 (pair2/pair3 = replications).
from pathlib import Path
import re
here=Path(__file__).resolve().parent; root=here.parents[3]; out=Path('/tmp/mh-register-attention'); out.mkdir(exist_ok=True)
src=(root/'hip/multihead_fused_attention.hip').read_text(); lines=src.split('\n')
SCORES_OLD=''' _Pragma("unroll 4") for(uint key=0;key<64;key+=16){f8 acc{};
  for(uint kt=0;kt<2;kt++){i2 a{},b{};uint qp=raster(win,first+rc(),width),kp=raster(win,key+rc(),width),off=kt*16+gr()*8;__builtin_memcpy(&a,normalized+qp*3*channels+head*32+off,8);__builtin_memcpy(&b,normalized+(kp*3+1)*channels+head*32+off,8);acc=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,acc);}
  _Pragma("unroll 8") for(uint e=0;e<8;e++){uint q=first+gr()*8+e,k=key+rc();float score=acc[e]+w[4*channels*channels+head*4096+q*64+k],affine=clampf(score*.044921875f+1.30078125f,1.03125f,1.5693359375f);uint ah=(bits(affine)>>13)-0x1c000u;ushort hb=static_cast<ushort>(((ah<<5)+0x8000u)&65535u);ex[q*66+k]=__builtin_bit_cast(_Float16,hb);saved_ex[key/16][e]=__builtin_bit_cast(_Float16,hb);}
 }
'''
SCORES_NEW=''' _Pragma("unroll 4") for(uint key=0;key<64;key+=16){f8 acc{};
  for(uint kt=0;kt<2;kt++){i2 a{},b{};uint qp=raster(win,first+rc(),width),kp=raster(win,key+rc(),width),off=kt*16+gr()*8;__builtin_memcpy(&a,normalized+qp*3*channels+head*32+off,8);__builtin_memcpy(&b,normalized+(kp*3+1)*channels+head*32+off,8);acc=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(b,a,acc);}
  h8 exv{};_Pragma("unroll 8") for(uint e=0;e<8;e++){uint q=first+rc(),k=key+gr()*8+e;float score=acc[e]+w[4*channels*channels+head*4096+q*64+k],affine=clampf(score*.044921875f+1.30078125f,1.03125f,1.5693359375f);uint ah=(bits(affine)>>13)-0x1c000u;ushort hb=static_cast<ushort>(((ah<<5)+0x8000u)&65535u);exv[e]=__builtin_bit_cast(_Float16,hb);}
  exfrag[key/16]=exv;
 }
'''
SUMS_OLD=''' f8 sums[2];for(uint side=0;side<2;side++){f8 sum{};for(uint half=0;half<2;half++){h8 a{},ones{};for(uint e=0;e<8;e++){uint k=side*16+half*32+gr()*8+e;a[e]=ex[(first+rc())*66+k];ones[e]=(_Float16)1.f;}sum=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(a,ones,sum);}sums[side]=sum;}
 uint pv[8]{};
 _Pragma("unroll 4") for(uint key=0;key<64;key+=16) _Pragma("unroll 8") for(uint e=0;e<8;e++){uint row=first+gr()*8+e,k=key+rc();float inv=1.f/(sums[0][e]+sums[1][e]);pv[e]|=fp8(float(saved_ex[key/16][e])*inv)<<(key/16*8);}
 sync_window();
 unsigned char*prob=reinterpret_cast<unsigned char*>(ex);
 #pragma unroll
 for(uint key=0;key<64;key+=16)for(uint e=0;e<8;e++)prob[(first+gr()*8+e)*68+key+rc()]=static_cast<unsigned char>(pv[e]>>(key/16*8));
 sync_window();
'''
SUMS_NEW=''' f8 sums[2];{h8 ones{};for(uint e=0;e<8;e++)ones[e]=(_Float16)1.f;
  _Pragma("unroll 2") for(uint side=0;side<2;side++){f8 sum{};_Pragma("unroll 2") for(uint half=0;half<2;half++)sum=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(ones,exfrag[side+2*half],sum);sums[side]=sum;}}
 _Pragma("unroll 4") for(uint kt=0;kt<4;kt++){i2 p{};_Pragma("unroll 8") for(uint e=0;e<8;e++){float inv=1.f/(sums[0][e]+sums[1][e]);put_bits(p,e,fp8(float(exfrag[kt][e])*inv));}pfrag[kt]=p;}
'''
AV_OLD='''   for(uint e=0;e<8;e++){uint k=kt*16+gr()*8+e;put_bits(a,e,prob[(first+rc())*68+k]);put_bits(b,e,packed[k*36+col+rc()]);}
'''
AV_NEW='''   a=pfrag[kt];for(uint e=0;e<8;e++){uint k=kt*16+gr()*8+e;put_bits(b,e,packed[k*36+col+rc()]);}
'''
def patch(name):
    start=next(i for i,l in enumerate(lines) if l.startswith(f'DEV void {name}_attention_project_body('))
    end=next(i for i in range(start,len(lines)) if lines[i]=='}')
    body='\n'.join(lines[start:end+1])
    def rep(old,new):
        nonlocal body
        assert body.count(old)==1,(name,old[:60],body.count(old))
        body=body.replace(old,new,1)
    rep(' h8 saved_ex[4];\n',' h8 exfrag[4];i2 pfrag[4];\n')
    body,n=re.subn(r' __attribute__\(\(shared\)\) _Float16 all_ex\[\d\*64\*66\];\n','',body,count=1); assert n==1
    body,n=re.subn(r' _Float16\*ex=all_ex\+(\w+)\*64\*66;unsigned char\*packed=all_packed\+(\w+)\*64\*36;\n',r' unsigned char*packed=all_packed+\2*64*36;\n',body,count=1); assert n==1
    # c64/c128 alias avbytes onto all_ex: give it its own (much smaller) LDS array, stride taken from its row indexing
    m=re.search(r'avbytes\[\(first\+gr\(\)\*8\+e\)\*(\d+)\+',body); assert m,(name,'avbytes stride')
    body,n=re.subn(r' unsigned char\*avbytes=reinterpret_cast<unsigned char\*>\(all_ex\);\n',f' __attribute__((shared)) unsigned char avbytes[64*{m.group(1)}];\n',body,count=1)
    print(name,'avbytes alias replaced' if n else 'avbytes already separate','stride',m.group(1))
    rep(SCORES_OLD,SCORES_NEW); rep(SUMS_OLD,SUMS_NEW); rep(AV_OLD,AV_NEW)
    # drop the sync right after the score loop and the one right after the AV block (either may be followed by #endif)
    body,n=re.subn(r'(  exfrag\[key/16\]=exv;\n \}\n(?:#endif\n)?) sync_window\(\);\n',r'\1',body,count=1); assert n==1,(name,'post-score sync')
    body,n=re.subn(r'(av\[col/16\]=acc;\}\n(?:#endif\n)?) sync_window\(\);\n',r'\1',body,count=1); assert n==1,(name,'post-av sync')
    compiled=re.sub(r'#if HIP_MH_ABLATE==\d\n.*?\n#else\n','',body,flags=re.S)
    compiled=re.sub(r'#if HIP_MH_VT\n.*?\n#else\n','',compiled,flags=re.S)
    assert 'all_ex' not in compiled and 'saved_ex' not in compiled and ' ex[' not in compiled and 'prob' not in compiled,(name,'leftover')
    print(name,'syncs left',body.count('sync_window();'))
    lines[start:end+1]=body.split('\n')
for nm in ('c64','c128','c256'): patch(nm)
text='#define HIP_ISA_HALF 1\n#define HIP_MH_RTZ_ISA 1\n'+'\n'.join(lines)+'\n'
(out/'multihead_fused_attention.generated.hip').write_text(text); print('written; exfrag sites',text.count('exfrag'))
