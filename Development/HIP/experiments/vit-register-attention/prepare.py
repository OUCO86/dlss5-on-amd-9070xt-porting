# ViT fused attention (vit_attention_fused_body, 400-token byte-input instance, 8 launches/frame): the per-key-tile
# LDS transpose (write t16 -> barrier -> read back) exists only to turn the score accumulator (lane = key) into the
# row fragment (lane = query, 8 consecutive keys). Swapping the score WMMA operands yields that fragment directly;
# the row-sum WMMA and the AV WMMA consume the same register values as before. 25 barriers per wave and t16 go away.
from pathlib import Path
here=Path(__file__).resolve().parent; root=here.parents[3]; out=Path('/tmp/vit-register-attention'); out.mkdir(exist_ok=True)
s=(root/'hip/deep_fast.hip').read_text()
def rep(old,new):
    global s
    assert s.count(old)==1,(old[:70],s.count(old)); s=s.replace(old,new,1)
rep(' __attribute__((shared)) unsigned short t16[2*16*24];\n','')
rep(''' for(uint key=0,tile=0;key<tokens;key+=16,tile^=1u){f8 a{};
  for(uint k=0;k<32;k+=16){i2 y{};if constexpr(ByteInput)__builtin_memcpy(&y,in8+(tokens+key+rc())*1024+head*32+k+gr()*8,8);else for(uint e=0;e<8;e++){uint j=k+gr()*8+e;pack(y,e,in[(tokens+key+rc())*1024+head*32+j]);}a=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(q[k/16],y,a);}
  unsigned short*t=t16+tile*16*24;
  for(uint e=0;e<8;e++){float af=clampf(a[e]*from_half(0x2dbb)+1.708984375f,1.439453125f,1.9775390625f);uint hb=(bits(af)>>13)-0x1c000u;t[(gr()*8+e)*24+rc()]=(unsigned short)(((hb<<4)+0x4000u)&65535u);}
  WG_FENCE(3);__builtin_amdgcn_s_barrier();WG_FENCE(2);
  h8 x{};i2 xb{};for(uint e=0;e<8;e++){unsigned short u=t[rc()*24+gr()*8+e];union{unsigned short u;_Float16 h;}cv;cv.u=u;x[e]=cv.h;pack(xb,e,from_half(u));}
''',''' for(uint key=0;key<tokens;key+=16){f8 a{};
  for(uint k=0;k<32;k+=16){i2 y{};if constexpr(ByteInput)__builtin_memcpy(&y,in8+(tokens+key+rc())*1024+head*32+k+gr()*8,8);else for(uint e=0;e<8;e++){uint j=k+gr()*8+e;pack(y,e,in[(tokens+key+rc())*1024+head*32+j]);}a=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(y,q[k/16],a);}
  // a is now the transposed score tile: lane = query row first+rc(), element e = key key+gr()*8+e -- the layout the
  // LDS round trip used to produce. Same per-element affine/half encoding.
  h8 x{};i2 xb{};for(uint e=0;e<8;e++){float af=clampf(a[e]*from_half(0x2dbb)+1.708984375f,1.439453125f,1.9775390625f);uint hb=(bits(af)>>13)-0x1c000u;unsigned short u=(unsigned short)(((hb<<4)+0x4000u)&65535u);union{unsigned short u;_Float16 h;}cv;cv.u=u;x[e]=cv.h;pack(xb,e,from_half(u));}
''')
rep(''' float inv[8];for(uint e=0;e<8;e++)inv[e]=1.f/sum[e];
 WG_FENCE(3);__builtin_amdgcn_s_barrier();WG_FENCE(2);
''',''' float inv[8];for(uint e=0;e<8;e++)inv[e]=1.f/sum[e];
''')
# Round 2: V stored transposed by the QKV producer ([head*32+col][key] after the Q/K rows) so the AV B fragment is one
# 8-byte load per lane instead of eight byte gathers (400 -> 50 loads per wave for 400 tokens); the producer's part-2
# store becomes one 8-byte store per lane instead of eight scattered bytes. Same bytes, same pack order.
rep(''' for(uint j=0;j<2;j++)for(uint e=0;e<8;e++){float v=acc[j][e];if(part<2){v*=__builtin_amdgcn_rsqf(maxf(sum[e],6.198883056640625e-5f))*scale;}out[(part*tokens+first+gr()*8+e)*1024+row+j*16+rc()]=byte_F(v);}
#else''',''' if(part==2){for(uint j=0;j<2;j++){unsigned long long word=0;for(uint e=0;e<8;e++)word|=(unsigned long long)(byte_F(acc[j][e])&255u)<<(8*e);__builtin_memcpy(out+size_t(2)*tokens*1024+size_t(row+j*16+rc())*tokens+first+gr()*8,&word,8);}}
 else for(uint j=0;j<2;j++)for(uint e=0;e<8;e++){float v=acc[j][e]*__builtin_amdgcn_rsqf(maxf(sum[e],6.198883056640625e-5f))*scale;out[(part*tokens+first+gr()*8+e)*1024+row+j*16+rc()]=byte_F(v);}
#else''')
rep('''  for(uint c=0;c<2;c++){i2 y{};for(uint e=0;e<8;e++){uint vkey=key+gr()*8+e;if constexpr(ByteInput){uint b=in8[(2*tokens+vkey)*1024+head*32+c*16+rc()];y[e/4]=int(uint(y[e/4])|(b<<(8*(e%4))));}else pack(y,e,in[(2*tokens+vkey)*1024+head*32+c*16+rc()]);}acc[c]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(xb,y,acc[c]);}''',
'''  for(uint c=0;c<2;c++){i2 y{};if constexpr(ByteInput)__builtin_memcpy(&y,in8+size_t(2)*tokens*1024+size_t(head*32+c*16+rc())*tokens+key+gr()*8,8);else for(uint e=0;e<8;e++){uint vkey=key+gr()*8+e;pack(y,e,in[(2*tokens+vkey)*1024+head*32+c*16+rc()]);}acc[c]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(xb,y,acc[c]);}''')
rep(''' for(uint j=0;j<2;j++)for(uint e=0;e<8;e++){float v=acc[j][e];if(part<2){float scale=part==0?5.65625f*w[1572864+row/32]:1.f;v*=__builtin_amdgcn_rsqf(maxf(sum[e],6.198883056640625e-5f))*scale;}out[(part*tokens+first+gr()*8+e)*1024+row+j*16+rc()]=byte_F(v);}
#endif''',''' if(part==2){for(uint j=0;j<2;j++){unsigned long long word=0;for(uint e=0;e<8;e++)word|=(unsigned long long)(byte_F(acc[j][e])&255u)<<(8*e);__builtin_memcpy(out+size_t(2)*tokens*1024+size_t(row+j*16+rc())*tokens+first+gr()*8,&word,8);}}
 else for(uint j=0;j<2;j++)for(uint e=0;e<8;e++){float v=acc[j][e];float scale=part==0?5.65625f*w[1572864+row/32]:1.f;v*=__builtin_amdgcn_rsqf(maxf(sum[e],6.198883056640625e-5f))*scale;out[(part*tokens+first+gr()*8+e)*1024+row+j*16+rc()]=byte_F(v);}
#endif''')
text='#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_BRANCHLESS_F 1\n'+s+'\n'
(out/'deep_fast-packed.generated.hip').write_text(text); print('ok')
