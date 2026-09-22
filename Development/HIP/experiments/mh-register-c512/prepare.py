# Register-resident ex/prob for mh_attention_fused_fp8_out (C512 attention, 13 launches/frame, 128-thread groups).
# Base = production source (already HIP_MH_REGISTER_EX for the c64/c128/c256 bodies). ex[64*66] (8.4 KB) goes,
# scores/row-sum WMMAs swap operands, prob packed in registers as the AV A fragment; three syncs become one.
from pathlib import Path
import re
here=Path(__file__).resolve().parent; root=here.parents[3]; out=Path('/tmp/mh-register-c512'); out.mkdir(exist_ok=True)
s=(root/'hip/multihead_fused_attention.hip').read_text()
k0=s.index('void mh_attention_fused_fp8_out('); k1=s.index('\n}\n',k0)+3
body=s[k0:k1]
def rep(old,new):
    global body
    assert body.count(old)==1,(old[:60],body.count(old)); body=body.replace(old,new,1)
rep(' __attribute__((shared)) _Float16 ex[64*66];\n',' h8 exfrag[4];i2 pfrag[4];\n')
rep(''' for(uint key=0;key<64;key+=16){f8 acc{};
  for(uint kt=0;kt<2;kt++){i2 a{},b{};for(uint e=0;e<8;e++){uint k=kt*16+gr()*8+e;put_bits(a,e,packed[(first+rc())*36+k]);put_bits(b,e,packed[(64+key+rc())*36+k]);}acc=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,acc);}
  for(uint e=0;e<8;e++){uint q=first+gr()*8+e,k=key+rc();float score=acc[e]+w[4*channels*channels+head*4096+q*64+k],affine=clampf(score*.044921875f+1.30078125f,1.03125f,1.5693359375f);uint ah=(bits(affine)>>13)-0x1c000u;ushort hb=static_cast<ushort>(((ah<<5)+0x8000u)&65535u);ex[q*66+k]=__builtin_bit_cast(_Float16,hb);}
 }
 sync_window();
''',''' _Pragma("unroll 4") for(uint key=0;key<64;key+=16){f8 acc{};
  for(uint kt=0;kt<2;kt++){i2 a{},b{};for(uint e=0;e<8;e++){uint k=kt*16+gr()*8+e;put_bits(a,e,packed[(first+rc())*36+k]);put_bits(b,e,packed[(64+key+rc())*36+k]);}acc=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(b,a,acc);}
  h8 exv{};_Pragma("unroll 8") for(uint e=0;e<8;e++){uint q=first+rc(),k=key+gr()*8+e;float score=acc[e]+w[4*channels*channels+head*4096+q*64+k],affine=clampf(score*.044921875f+1.30078125f,1.03125f,1.5693359375f);uint ah=(bits(affine)>>13)-0x1c000u;ushort hb=static_cast<ushort>(((ah<<5)+0x8000u)&65535u);exv[e]=__builtin_bit_cast(_Float16,hb);}
  exfrag[key/16]=exv;
 }
''')
rep(''' f8 sums[2];for(uint side=0;side<2;side++){f8 sum{};for(uint half=0;half<2;half++){h8 a{},ones{};for(uint e=0;e<8;e++){uint k=side*16+half*32+gr()*8+e;a[e]=ex[(first+rc())*66+k];ones[e]=(_Float16)1.f;}sum=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(a,ones,sum);}sums[side]=sum;}
 // Q/K are dead; probability64x68 occupies4352 of their4608 bytes. V starts4608.
 for(uint key=0;key<64;key+=16)for(uint e=0;e<8;e++){uint row=first+gr()*8+e,k=key+rc();float inv=1.f/(sums[0][e]+sums[1][e]);packed[row*68+k]=static_cast<unsigned char>(fp8(float(ex[row*66+k])*inv));}
 sync_window();
''',''' f8 sums[2];{h8 ones{};for(uint e=0;e<8;e++)ones[e]=(_Float16)1.f;
  _Pragma("unroll 2") for(uint side=0;side<2;side++){f8 sum{};_Pragma("unroll 2") for(uint half=0;half<2;half++)sum=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(ones,exfrag[side+2*half],sum);sums[side]=sum;}}
 _Pragma("unroll 4") for(uint kt=0;kt<4;kt++){i2 p{};_Pragma("unroll 8") for(uint e=0;e<8;e++){float inv=1.f/(sums[0][e]+sums[1][e]);put_bits(p,e,fp8(float(exfrag[kt][e])*inv));}pfrag[kt]=p;}
''')
rep(''' for(uint col=0;col<32;col+=16){f8 acc{};for(uint kt=0;kt<4;kt++){i2 a{},b{};for(uint e=0;e<8;e++){uint k=kt*16+gr()*8+e;put_bits(a,e,packed[(first+rc())*68+k]);put_bits(b,e,packed[(128+k)*36+col+rc()]);}''',
    ''' for(uint col=0;col<32;col+=16){f8 acc{};for(uint kt=0;kt<4;kt++){i2 a=pfrag[kt],b{};for(uint e=0;e<8;e++){uint k=kt*16+gr()*8+e;put_bits(b,e,packed[(128+k)*36+col+rc()]);}''')
assert body.count('sync_window();')==1 and ' ex[' not in body and 'ex[64' not in body
text='#define HIP_ISA_HALF 1\n#define HIP_MH_RTZ_ISA 1\n'+s[:k0]+body+s[k1:]+'\n'
(out/'multihead_fused_attention.generated.hip').write_text(text); print('ok, syncs',body.count('sync_window();'))
