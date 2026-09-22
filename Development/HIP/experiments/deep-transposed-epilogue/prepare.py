# "Transposed epilogue" for C512 split_projection_frag (13 launches/frame, single-wave): the accumulator only feeds the
# residual init, F(H()) and two stores per element. Swapping the WMMA operands makes each lane hold one row with 8
# consecutive columns, so the f32 output and the tiled E4M3 copy become vector stores and the residual becomes vector
# loads. Element arithmetic unchanged -> bit-exact. Base = production (prod5). pair1 only; pair2/3 = replications.
from pathlib import Path
here=Path(__file__).resolve().parent; root=here.parents[3]; out=Path('/tmp/deep-transposed-epilogue'); out.mkdir(exist_ok=True)
s=(root/'hip/deep_fast.hip').read_text()
def rep(old,new):
    global s
    assert s.count(old)==1,(old[:70],s.count(old)); s=s.replace(old,new,1)
rep(''' for(uint j=0;j<4;j++)for(uint e=0;e<8;e++)acc[j][e]=H(skip[(first+gr()*8+e)*512+row+j*16+rc()]*w[262144+row+j*16+rc()]);
 const unsigned char*wb=reinterpret_cast<const unsigned char*>(w);const unsigned char*arow=in8+((first/16)*16)*512+rc()*32+gr()*8;
 for(uint gs=0;gs<16;gs++)for(uint h=0;h<2;h++){i2 a;__builtin_memcpy(&a,arow+gs*512+h*16,8);
  for(uint j=0;j<4;j++){uint n0=row+j*16+rc();i2 b;__builtin_memcpy(&b,wb+((n0/16)*16+gs)*512+((h*2+gr())*16+n0%16)*8,8);acc[j]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,acc[j]);}}
 for(uint j=0;j<4;j++)for(uint e=0;e<8;e++){uint r=first+gr()*8+e,c=row+j*16+rc();float v=F(H(acc[j][e]));out[r*512+c]=v;out8[((r/16)*16+c/32)*512+(r%16)*32+c%32]=static_cast<unsigned char>(__builtin_amdgcn_cvt_pk_fp8_f32(v,0.f,0,false));}
}''',''' // Transposed epilogue: lane = row first+rc(), element e = column row+j*16+gr()*8+e (swapped WMMA operands).
 {const uint r=first+rc();for(uint j=0;j<4;j++){const uint c0=row+j*16+gr()*8;f4 sk0,sk1,ws0,ws1;__builtin_memcpy(&sk0,skip+size_t(r)*512+c0,16);__builtin_memcpy(&sk1,skip+size_t(r)*512+c0+4,16);__builtin_memcpy(&ws0,w+262144+c0,16);__builtin_memcpy(&ws1,w+262144+c0+4,16);
  for(uint e=0;e<4;e++){acc[j][e]=H(sk0[e]*ws0[e]);acc[j][4+e]=H(sk1[e]*ws1[e]);}}}
 const unsigned char*wb=reinterpret_cast<const unsigned char*>(w);const unsigned char*arow=in8+((first/16)*16)*512+rc()*32+gr()*8;
 for(uint gs=0;gs<16;gs++)for(uint h=0;h<2;h++){i2 a;__builtin_memcpy(&a,arow+gs*512+h*16,8);
  for(uint j=0;j<4;j++){uint n0=row+j*16+rc();i2 b;__builtin_memcpy(&b,wb+((n0/16)*16+gs)*512+((h*2+gr())*16+n0%16)*8,8);acc[j]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(b,a,acc[j]);}}
 {const uint r=first+rc();for(uint j=0;j<4;j++){const uint c0=row+j*16+gr()*8;f4 v0,v1;unsigned long long bytes=0;
  for(uint e=0;e<4;e++){float v=F(H(acc[j][e]));v0[e]=v;bytes|=(unsigned long long)(__builtin_amdgcn_cvt_pk_fp8_f32(v,0.f,0,false)&255u)<<(8*e);}
  for(uint e=0;e<4;e++){float v=F(H(acc[j][4+e]));v1[e]=v;bytes|=(unsigned long long)(__builtin_amdgcn_cvt_pk_fp8_f32(v,0.f,0,false)&255u)<<(8*(4+e));}
  __builtin_memcpy(out+size_t(r)*512+c0,&v0,16);__builtin_memcpy(out+size_t(r)*512+c0+4,&v1,16);
  __builtin_memcpy(out8+((r/16)*16+c0/32)*512+(r%16)*32+c0%32,&bytes,8);}}
}''')
s=s.replace('using i2=int __attribute__((ext_vector_type(2)));','using i2=int __attribute__((ext_vector_type(2)));\nusing f4=float __attribute__((ext_vector_type(4)));',1) if 'using f4=' not in s else s
assert 'using f4=' in s
text='#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_BRANCHLESS_F 1\n'+s+'\n'
(out/'deep_fast-packed.generated.hip').write_text(text); print('ok')
