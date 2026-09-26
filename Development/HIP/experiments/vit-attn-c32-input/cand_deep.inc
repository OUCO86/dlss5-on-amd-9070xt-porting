// ===== vit-attn-c32-input candidates (appended to deep_fast.hip) =====
// A1 "m32": one wave = TWO 16-query tiles x one head. Per key tile the K fragment and both V fragments are loaded once and
// feed both query tiles' MMAs. Every per-query operation (QK MMA K order, exp bit map, LDS transpose, f16 denominator MMA in
// key order, FP8 PV MMA, epilogue F(Hrtz(acc*inv))) is exactly vit_attention_fused_body's, so the output is bit-identical.
// Grid: ceil(tiles/2) x 32 heads. The second tile of the last wave may lie beyond `tokens` (odd tile count: 400 tokens =
// 25 tiles); it is computed on in-buffer rows and simply not stored.
template<uint MAXT,bool ByteInput=true,bool ByteOut=false>
DEV void vit_attention_fused_m32_body(const float*in,float*out,uint tokens){
 uint head=bid()%32,first=bid()/32*32;if(first>=tokens)return;const bool two=first+16<tokens;
 __attribute__((shared)) unsigned short t16[2*2*16*24];
 const unsigned char*in8=reinterpret_cast<const unsigned char*>(in);
 i2 q0[2]{},q1[2]{};
 for(uint k=0;k<32;k+=16){
  if constexpr(ByteInput){__builtin_memcpy(&q0[k/16],in8+(first+rc())*1024+head*32+k+gr()*8,8);__builtin_memcpy(&q1[k/16],in8+(first+16+rc())*1024+head*32+k+gr()*8,8);}
  else for(uint e=0;e<8;e++){uint j=k+gr()*8+e;pack(q0[k/16],e,in[(first+rc())*1024+head*32+j]);pack(q1[k/16],e,in[(first+16+rc())*1024+head*32+j]);}
 }
 h8 ones{};for(uint e=0;e<8;e++)ones[e]=(_Float16)1.f;
 f8 sum0{},sum1{},acc0[2]{},acc1[2]{};
 for(uint key=0,tile=0;key<tokens;key+=16,tile^=1u){f8 a0{},a1{};
  for(uint k=0;k<32;k+=16){i2 y{};if constexpr(ByteInput)__builtin_memcpy(&y,in8+(tokens+key+rc())*1024+head*32+k+gr()*8,8);else for(uint e=0;e<8;e++){uint j=k+gr()*8+e;pack(y,e,in[(tokens+key+rc())*1024+head*32+j]);}
   a0=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(q0[k/16],y,a0);a1=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(q1[k/16],y,a1);}
  unsigned short*t0=t16+tile*2*16*24,*t1=t0+16*24;
  for(uint e=0;e<8;e++){
   float af=clampf(a0[e]*from_half(0x2dbb)+1.708984375f,1.439453125f,1.9775390625f);uint hb=(bits(af)>>13)-0x1c000u;t0[(gr()*8+e)*24+rc()]=(unsigned short)(((hb<<4)+0x4000u)&65535u);
   af=clampf(a1[e]*from_half(0x2dbb)+1.708984375f,1.439453125f,1.9775390625f);hb=(bits(af)>>13)-0x1c000u;t1[(gr()*8+e)*24+rc()]=(unsigned short)(((hb<<4)+0x4000u)&65535u);}
  WG_FENCE(3);__builtin_amdgcn_s_barrier();WG_FENCE(2);
  h8 x0{},x1{};i2 xb0{},xb1{};
  for(uint e=0;e<8;e++){union{unsigned short u;_Float16 h;}cv;
   unsigned short u=t0[rc()*24+gr()*8+e];cv.u=u;x0[e]=cv.h;pack(xb0,e,from_half(u));
   u=t1[rc()*24+gr()*8+e];cv.u=u;x1[e]=cv.h;pack(xb1,e,from_half(u));}
  sum0=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(x0,ones,sum0);sum1=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(x1,ones,sum1);
  for(uint c=0;c<2;c++){i2 y{};for(uint e=0;e<8;e++){uint vkey=key+gr()*8+e;if constexpr(ByteInput){uint b=in8[(2*tokens+vkey)*1024+head*32+c*16+rc()];y[e/4]=int(uint(y[e/4])|(b<<(8*(e%4))));}else pack(y,e,in[(2*tokens+vkey)*1024+head*32+c*16+rc()]);}
   acc0[c]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(xb0,y,acc0[c]);acc1[c]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(xb1,y,acc1[c]);}
 }
 float inv0[8],inv1[8];for(uint e=0;e<8;e++){inv0[e]=1.f/sum0[e];inv1[e]=1.f/sum1[e];}
 WG_FENCE(3);__builtin_amdgcn_s_barrier();WG_FENCE(2);
 for(uint c=0;c<2;c++)for(uint e=0;e<8;e++){
  if constexpr(ByteOut)reinterpret_cast<unsigned char*>(out)[(first+gr()*8+e)*1024+head*32+c*16+rc()]=byte_F(Hrtz(acc0[c][e]*inv0[e]));
  else out[(first+gr()*8+e)*1024+head*32+c*16+rc()]=F(Hrtz(acc0[c][e]*inv0[e]));}
 if(two)for(uint c=0;c<2;c++)for(uint e=0;e<8;e++){
  if constexpr(ByteOut)reinterpret_cast<unsigned char*>(out)[(first+16+gr()*8+e)*1024+head*32+c*16+rc()]=byte_F(Hrtz(acc1[c][e]*inv1[e]));
  else out[(first+16+gr()*8+e)*1024+head*32+c*16+rc()]=F(Hrtz(acc1[c][e]*inv1[e]));}
}
WAVE void vit_attention_fused_256_bytein_m32(const float*in,float*out,uint tokens,const uint*reuse_gate){if(reuse_gate&&reuse_gate[0])return;vit_attention_fused_m32_body<256,true>(in,out,tokens);}
WAVE void vit_attention_fused_400_bytein_m32(const float*in,float*out,uint tokens,const uint*reuse_gate){if(reuse_gate&&reuse_gate[0])return;vit_attention_fused_m32_body<400,true>(in,out,tokens);}
WAVE void vit_attention_fused_640_bytein_m32(const float*in,float*out,uint tokens,const uint*reuse_gate){if(reuse_gate&&reuse_gate[0])return;vit_attention_fused_m32_body<640,true>(in,out,tokens);}
// A2 "vt": V stored transposed. Producer = vit_qkv_project_normalize_fused_f16compact_fp8_frag with the V part (part 2)
// written to out + 2*tokens*1024 as [channel][token] bytes (Q/K unchanged); each lane's 8 V bytes (8 consecutive tokens,
// one channel) become one 8-byte store. Consumer = vit_attention_fused_body with the two per-tile V B-fragments read as one
// 8-byte load each (8 consecutive keys of one channel) instead of 8 byte gathers 1 KiB apart. Same bytes, same packing
// order (key e -> byte e), so the output is bit-identical.
WAVE void vit_qkv_project_normalize_fused_f16compact_fp8_frag_vt(const float*in,const float*w,unsigned char*out,uint tokens,const uint*reuse_gate){if(reuse_gate&&reuse_gate[0])return;
 uint perpart=(tokens/16)*32,part=bid()/perpart,local=bid()%perpart,first=local/32*16,row=local%32*32;if(part>=3)return;f8 acc[2]{};
 const _Float16*w16=reinterpret_cast<const _Float16*>(w)+part*1048576;
 for(uint k=0;k<1024;k+=16){h8 a{};for(uint e=0;e<8;e++)a[e]=(_Float16)in[(first+rc())*1024+k+gr()*8+e];for(uint j=0;j<2;j++){h8 b{};__builtin_memcpy(&b,w16+(((row+j*16)/16)*64+k/16)*256+(gr()*16+rc())*8,16);acc[j]=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(a,b,acc[j]);}}
 if(part==2){for(uint j=0;j<2;j++){unsigned long long pk=0;for(uint e=0;e<8;e++)pk|=(unsigned long long)byte_F(acc[j][e])<<(8*e);
   __builtin_memcpy(out+size_t(2*tokens)*1024+size_t(row+j*16+rc())*tokens+first+gr()*8,&pk,8);}return;}
 __attribute__((shared)) float raw[16*33];
 f8 sum{};
 for(uint j=0;j<2;j++)for(uint e=0;e<8;e++)raw[(gr()*8+e)*33+j*16+rc()]=acc[j][e];
 __builtin_amdgcn_s_barrier();
 for(uint k=0;k<32;k+=16){h8 x{},ones{};for(uint e=0;e<8;e++){float v=raw[rc()*33+k+gr()*8+e];x[e]=(_Float16)(v*v);ones[e]=(_Float16)1.f;}sum=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(x,ones,sum);}
 for(uint j=0;j<2;j++)for(uint e=0;e<8;e++){float v=acc[j][e];float scale=part==0?5.65625f*w[1572864+row/32]:1.f;v*=__builtin_amdgcn_rsqf(maxf(sum[e],6.198883056640625e-5f))*scale;out[(part*tokens+first+gr()*8+e)*1024+row+j*16+rc()]=byte_F(v);}
}
template<uint MAXT>
DEV void vit_attention_fused_vt_body(const float*in,float*out,uint tokens){
 uint head=bid()%32,first=bid()/32*16;if(first>=tokens)return;
 __attribute__((shared)) unsigned short t16[2*16*24];
 const unsigned char*in8=reinterpret_cast<const unsigned char*>(in);const unsigned char*vt=in8+size_t(2*tokens)*1024;
 i2 q[2]{};for(uint k=0;k<32;k+=16)__builtin_memcpy(&q[k/16],in8+(first+rc())*1024+head*32+k+gr()*8,8);
 h8 ones{};for(uint e=0;e<8;e++)ones[e]=(_Float16)1.f;
 f8 sum{},acc[2]{};
 for(uint key=0,tile=0;key<tokens;key+=16,tile^=1u){f8 a{};
  for(uint k=0;k<32;k+=16){i2 y{};__builtin_memcpy(&y,in8+(tokens+key+rc())*1024+head*32+k+gr()*8,8);a=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(q[k/16],y,a);}
  unsigned short*t=t16+tile*16*24;
  for(uint e=0;e<8;e++){float af=clampf(a[e]*from_half(0x2dbb)+1.708984375f,1.439453125f,1.9775390625f);uint hb=(bits(af)>>13)-0x1c000u;t[(gr()*8+e)*24+rc()]=(unsigned short)(((hb<<4)+0x4000u)&65535u);}
  WG_FENCE(3);__builtin_amdgcn_s_barrier();WG_FENCE(2);
  h8 x{};i2 xb{};for(uint e=0;e<8;e++){unsigned short u=t[rc()*24+gr()*8+e];union{unsigned short u;_Float16 h;}cv;cv.u=u;x[e]=cv.h;pack(xb,e,from_half(u));}
  sum=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(x,ones,sum);
  for(uint c=0;c<2;c++){i2 y{};__builtin_memcpy(&y,vt+size_t(head*32+c*16+rc())*tokens+key+gr()*8,8);acc[c]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(xb,y,acc[c]);}
 }
 float inv[8];for(uint e=0;e<8;e++)inv[e]=1.f/sum[e];
 WG_FENCE(3);__builtin_amdgcn_s_barrier();WG_FENCE(2);
 for(uint c=0;c<2;c++)for(uint e=0;e<8;e++)out[(first+gr()*8+e)*1024+head*32+c*16+rc()]=F(Hrtz(acc[c][e]*inv[e]));
}
WAVE void vit_attention_fused_256_bytein_vt(const float*in,float*out,uint tokens,const uint*reuse_gate){if(reuse_gate&&reuse_gate[0])return;vit_attention_fused_vt_body<256>(in,out,tokens);}
WAVE void vit_attention_fused_400_bytein_vt(const float*in,float*out,uint tokens,const uint*reuse_gate){if(reuse_gate&&reuse_gate[0])return;vit_attention_fused_vt_body<400>(in,out,tokens);}
WAVE void vit_attention_fused_640_bytein_vt(const float*in,float*out,uint tokens,const uint*reuse_gate){if(reuse_gate&&reuse_gate[0])return;vit_attention_fused_vt_body<640>(in,out,tokens);}
// A3 "swap": scores computed as S^T = K*Q^T by swapping the QK WMMA operands (A/B fragments share the register layout; the
// swapped MMA yields the transposed tile, bit-exact as established for prod6's folded FFN). The accumulator then already
// holds, per lane, query rc() x keys gr()*8+e -- exactly the A-operand layout the denominator (f16 x ones) and PV (fp8) MMAs
// consume -- so the per-tile LDS transpose, its two fences and the s_barrier disappear. Per-element exp bit map, denominator
// and PV operand values and K order are unchanged, hence bit-identical output.
template<uint MAXT>
DEV void vit_attention_fused_swap_body(const float*in,float*out,uint tokens){
 uint head=bid()%32,first=bid()/32*16;if(first>=tokens)return;
 const unsigned char*in8=reinterpret_cast<const unsigned char*>(in);
 i2 q[2]{};for(uint k=0;k<32;k+=16)__builtin_memcpy(&q[k/16],in8+(first+rc())*1024+head*32+k+gr()*8,8);
 h8 ones{};for(uint e=0;e<8;e++)ones[e]=(_Float16)1.f;
 f8 sum{},acc[2]{};
 for(uint key=0;key<tokens;key+=16){f8 a{};
  for(uint k=0;k<32;k+=16){i2 y{};__builtin_memcpy(&y,in8+(tokens+key+rc())*1024+head*32+k+gr()*8,8);a=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(y,q[k/16],a);}
  h8 x{};i2 xb{};
  for(uint e=0;e<8;e++){float af=clampf(a[e]*from_half(0x2dbb)+1.708984375f,1.439453125f,1.9775390625f);uint hb=(bits(af)>>13)-0x1c000u;unsigned short u=(unsigned short)(((hb<<4)+0x4000u)&65535u);
   union{unsigned short u;_Float16 h;}cv;cv.u=u;x[e]=cv.h;pack(xb,e,from_half(u));}
  sum=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(x,ones,sum);
  for(uint c=0;c<2;c++){i2 y{};for(uint e=0;e<8;e++){uint vkey=key+gr()*8+e;uint b=in8[(2*tokens+vkey)*1024+head*32+c*16+rc()];y[e/4]=int(uint(y[e/4])|(b<<(8*(e%4))));}acc[c]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(xb,y,acc[c]);}
 }
 float inv[8];for(uint e=0;e<8;e++)inv[e]=1.f/sum[e];
 for(uint c=0;c<2;c++)for(uint e=0;e<8;e++)out[(first+gr()*8+e)*1024+head*32+c*16+rc()]=F(Hrtz(acc[c][e]*inv[e]));
}
WAVE void vit_attention_fused_256_bytein_swap(const float*in,float*out,uint tokens,const uint*reuse_gate){if(reuse_gate&&reuse_gate[0])return;vit_attention_fused_swap_body<256>(in,out,tokens);}
WAVE void vit_attention_fused_400_bytein_swap(const float*in,float*out,uint tokens,const uint*reuse_gate){if(reuse_gate&&reuse_gate[0])return;vit_attention_fused_swap_body<400>(in,out,tokens);}
WAVE void vit_attention_fused_640_bytein_swap(const float*in,float*out,uint tokens,const uint*reuse_gate){if(reuse_gate&&reuse_gate[0])return;vit_attention_fused_swap_body<640>(in,out,tokens);}
// A4 = A2 + A3: transposed V (from the _vt producer) + swapped QK without LDS transpose.
template<uint MAXT>
DEV void vit_attention_fused_swapvt_body(const float*in,float*out,uint tokens){
 uint head=bid()%32,first=bid()/32*16;if(first>=tokens)return;
 const unsigned char*in8=reinterpret_cast<const unsigned char*>(in);const unsigned char*vt=in8+size_t(2*tokens)*1024;
 i2 q[2]{};for(uint k=0;k<32;k+=16)__builtin_memcpy(&q[k/16],in8+(first+rc())*1024+head*32+k+gr()*8,8);
 h8 ones{};for(uint e=0;e<8;e++)ones[e]=(_Float16)1.f;
 f8 sum{},acc[2]{};
 for(uint key=0;key<tokens;key+=16){f8 a{};
  for(uint k=0;k<32;k+=16){i2 y{};__builtin_memcpy(&y,in8+(tokens+key+rc())*1024+head*32+k+gr()*8,8);a=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(y,q[k/16],a);}
  h8 x{};i2 xb{};
  for(uint e=0;e<8;e++){float af=clampf(a[e]*from_half(0x2dbb)+1.708984375f,1.439453125f,1.9775390625f);uint hb=(bits(af)>>13)-0x1c000u;unsigned short u=(unsigned short)(((hb<<4)+0x4000u)&65535u);
   union{unsigned short u;_Float16 h;}cv;cv.u=u;x[e]=cv.h;pack(xb,e,from_half(u));}
  sum=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(x,ones,sum);
  for(uint c=0;c<2;c++){i2 y{};__builtin_memcpy(&y,vt+size_t(head*32+c*16+rc())*tokens+key+gr()*8,8);acc[c]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(xb,y,acc[c]);}
 }
 float inv[8];for(uint e=0;e<8;e++)inv[e]=1.f/sum[e];
 for(uint c=0;c<2;c++)for(uint e=0;e<8;e++)out[(first+gr()*8+e)*1024+head*32+c*16+rc()]=F(Hrtz(acc[c][e]*inv[e]));
}
WAVE void vit_attention_fused_256_bytein_swapvt(const float*in,float*out,uint tokens,const uint*reuse_gate){if(reuse_gate&&reuse_gate[0])return;vit_attention_fused_swapvt_body<256>(in,out,tokens);}
WAVE void vit_attention_fused_400_bytein_swapvt(const float*in,float*out,uint tokens,const uint*reuse_gate){if(reuse_gate&&reuse_gate[0])return;vit_attention_fused_swapvt_body<400>(in,out,tokens);}
WAVE void vit_attention_fused_640_bytein_swapvt(const float*in,float*out,uint tokens,const uint*reuse_gate){if(reuse_gate&&reuse_gate[0])return;vit_attention_fused_swapvt_body<640>(in,out,tokens);}
