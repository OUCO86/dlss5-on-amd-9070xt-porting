# Transposed projection/QKV tail for mh_ffn_qkv_body (bit-exact): swapping the WMMA operands yields D^T, so a lane holds
# one token row and 8 consecutive columns (WMMA A/B fragment register layouts are identical, verified in C32/mh).
# Every read/write in the tail becomes 8 consecutive elements per lane; the serial 32-term sum of squares (LDS, 128
# threads) keeps its order, so norm/out are identical bits. Non-BatchNorm path only (production).
#   pair1: index transposition, scalar loads/stores (compiler may merge)   pair2: pair1 + explicit 8-byte memcpy   pair3 = pair1
from pathlib import Path
import shutil
here=Path(__file__).resolve().parent; root=here.parents[3]; out=Path('/tmp/mhfast-transposed-qkv')
for sub in ('pair1','pair2','pair3'): shutil.rmtree(out/sub, ignore_errors=True); (out/sub).mkdir(parents=True)
s0=(root/'hip/multihead_fast_padded.hip').read_text()
W='__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12'
R=[
('  f8 result{};{const float rs=w[9*C*C+wave*16+rc];float rv[8];\n   for(uint e=0;e<8;e++){if constexpr(ByteIn)rv[e]=ffn_input8_nb<C,Mapped>(in8,first+group*8+e,wave*16+rc,width,height,workw,sx,sy);else rv[e]=ffn_input_nb<C,Mapped>(in,first+group*8+e,wave*16+rc,width,height,workw,sx,sy);}\n   for(uint e=0;e<8;e++)result[e]=Hrtz(rv[e]*rs);}\n',
 '  f8 result{};{float rv[8],rs[8];\n   for(uint e=0;e<8;e++){uint c=wave*16+group*8+e;rs[e]=w[9*C*C+c];if constexpr(ByteIn)rv[e]=ffn_input8_nb<C,Mapped>(in8,first+rc,c,width,height,workw,sx,sy);else rv[e]=ffn_input_nb<C,Mapped>(in,first+rc,c,width,height,workw,sx,sy);}\n   for(uint e=0;e<8;e++)result[e]=Hrtz(rv[e]*rs[e]);}\n'),
('  f8 result{};for(uint e=0;e<8;e++)result[e]=Hrtz(load_in(first+group*8+e,wave*16+rc)*w[9*C*C+wave*16+rc]);\n',
 '  f8 result{};for(uint e=0;e<8;e++)result[e]=Hrtz(load_in(first+rc,wave*16+group*8+e)*w[9*C*C+wave*16+group*8+e]);\n'),
('  for(uint k=0;k<C;k+=16){i2 a,b;__builtin_memcpy(&a,hidden+rc*(C+4)+k+group*8,8);uint off=8*C*C+((wave*16+rc)*C+k+group*8)/4;if constexpr(Frag)b=frag_b(reinterpret_cast<const unsigned char*>(w+8*C*C),wave*16+rc,C,k,group);else b={int(pw[off]),int(pw[off+1])};result='+W+'(a,b,result);}\n',
 '  for(uint k=0;k<C;k+=16){i2 a,b;__builtin_memcpy(&a,hidden+rc*(C+4)+k+group*8,8);uint off=8*C*C+((wave*16+rc)*C+k+group*8)/4;if constexpr(Frag)b=frag_b(reinterpret_cast<const unsigned char*>(w+8*C*C),wave*16+rc,C,k,group);else b={int(pw[off]),int(pw[off+1])};result='+W+'(b,a,result);}\n'),
('  for(uint e=0;e<8;e++){uint byte=q8_fused_round(result[e]);float v=__builtin_amdgcn_cvt_f32_fp8(int(byte),0);if constexpr(ByteFeature)out[(first+group*8+e)*C+wave*16+rc]=static_cast<unsigned char>(byte);else reinterpret_cast<float*>(out)[(first+group*8+e)*C+wave*16+rc]=v;qfeature[(group*8+e)*(C+4)+wave*16+rc]=static_cast<unsigned char>(byte);}\n',
 '  for(uint e=0;e<8;e++){uint byte=q8_fused_round(result[e]);float v=__builtin_amdgcn_cvt_f32_fp8(int(byte),0);uint c=wave*16+group*8+e;if constexpr(ByteFeature)out[(first+rc)*C+c]=static_cast<unsigned char>(byte);else reinterpret_cast<float*>(out)[(first+rc)*C+c]=v;qfeature[rc*(C+4)+c]=static_cast<unsigned char>(byte);}\n'),
('   for(uint k=0;k<C;k+=16){i2 a,b;__builtin_memcpy(&a,qfeature+rc*(C+4)+k+group*8,8);uint off=((part*C+wave*16+rc)*C+k+group*8)/4;if constexpr(Frag)b=frag_b(reinterpret_cast<const unsigned char*>(aw),part*C+wave*16+rc,C,k,group);else b={int(aq[off]),int(aq[off+1])};q='+W+'(a,b,q);}\n',
 '   for(uint k=0;k<C;k+=16){i2 a,b;__builtin_memcpy(&a,qfeature+rc*(C+4)+k+group*8,8);uint off=((part*C+wave*16+rc)*C+k+group*8)/4;if constexpr(Frag)b=frag_b(reinterpret_cast<const unsigned char*>(aw),part*C+wave*16+rc,C,k,group);else b={int(aq[off]),int(aq[off+1])};q='+W+'(b,a,q);}\n'),
('   if(part<2){for(uint e=0;e<8;e++)storage.raw[((wave/2)*16+group*8+e)*33+(wave%2)*16+rc]=q[e];\n',
 '   if(part<2){for(uint e=0;e<8;e++)storage.raw[((wave/2)*16+rc)*33+(wave%2)*16+group*8+e]=q[e];\n'),
('   for(uint e=0;e<8;e++){uint row=group*8+e;float inv=part<2?inverse[(wave/2)*16+row]:1.f;norm[((first+row)*3+part)*C+wave*16+rc]=static_cast<unsigned char>(q8_fused_round(q[e]*inv));}\n',
 '   {float inv=part<2?inverse[(wave/2)*16+rc]:1.f;for(uint e=0;e<8;e++)norm[((first+rc)*3+part)*C+wave*16+group*8+e]=static_cast<unsigned char>(q8_fused_round(q[e]*inv));}\n'),
]
s1=s0
for o,n in R:
    assert s1.count(o)==1,(o[:70],s1.count(o)); s1=s1.replace(o,n,1)
# pair2: explicit 8-byte vector stores for out / qfeature / norm (same bytes, same addresses)
V=[
('uint c=wave*16+group*8+e;if constexpr(ByteFeature)out[(first+rc)*C+c]=static_cast<unsigned char>(byte);else reinterpret_cast<float*>(out)[(first+rc)*C+c]=v;qfeature[rc*(C+4)+c]=static_cast<unsigned char>(byte);}\n',
 'uint c=wave*16+group*8+e;if constexpr(!ByteFeature)reinterpret_cast<float*>(out)[(first+rc)*C+c]=v;ob[e]=static_cast<unsigned char>(byte);}\n   if constexpr(ByteFeature)__builtin_memcpy(out+(first+rc)*C+wave*16+group*8,ob,8);__builtin_memcpy(qfeature+rc*(C+4)+wave*16+group*8,ob,8);\n'),
('  for(uint e=0;e<8;e++){uint byte=q8_fused_round(result[e]);float v=__builtin_amdgcn_cvt_f32_fp8(int(byte),0);uint c=wave*16+group*8+e;if constexpr(!ByteFeature)',
 '  unsigned char ob[8];for(uint e=0;e<8;e++){uint byte=q8_fused_round(result[e]);float v=__builtin_amdgcn_cvt_f32_fp8(int(byte),0);uint c=wave*16+group*8+e;if constexpr(!ByteFeature)'),
('   {float inv=part<2?inverse[(wave/2)*16+rc]:1.f;for(uint e=0;e<8;e++)norm[((first+rc)*3+part)*C+wave*16+group*8+e]=static_cast<unsigned char>(q8_fused_round(q[e]*inv));}\n',
 '   {float inv=part<2?inverse[(wave/2)*16+rc]:1.f;unsigned char nb[8];for(uint e=0;e<8;e++)nb[e]=static_cast<unsigned char>(q8_fused_round(q[e]*inv));__builtin_memcpy(norm+((first+rc)*3+part)*C+wave*16+group*8,nb,8);}\n'),
]
s2=s1
for o,n in V:
    assert s2.count(o)==1,(o[:70],s2.count(o)); s2=s2.replace(o,n,1)
for m,s in {1:s1,2:s2,3:s1}.items():
    (out/f'pair{m}'/'multihead-fast-padded-wave-packed.generated.hip').write_text('#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_FFN_HOIST_RES 2\n'+s+'\n')
print('written')
