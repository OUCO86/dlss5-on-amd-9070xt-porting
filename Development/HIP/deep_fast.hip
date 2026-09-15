// Production ViT matrix math. FP8 MLP, F16 QKV, raw FP32 accumulation.
// Flat grid ceil(output_work_items/256), block32. One block = 16 tokens x 16 channels.
// Tokens and output channels must be divisible by16; no scalar GEMM fallback.
#pragma clang fp contract(off)
#pragma clang fp reassociate(off)
typedef unsigned uint;
#define DEV __attribute__((device)) __attribute__((always_inline))
#define KERNEL extern "C" __attribute__((global))
DEV uint bits(float x){union{float f;uint u;}v;v.f=x;return v.u;}
DEV float value(uint x){union{float f;uint u;}v;v.u=x;return v.f;}
DEV float absf(float x){return value(bits(x)&0x7fffffffu);}
DEV float maxf(float a,float b){return a>b?a:b;}
DEV float minf(float a,float b){return a<b?a:b;}
DEV float clampf(float a,float lo,float hi){return minf(maxf(a,lo),hi);}
DEV uint shift_rne(uint x,uint n){if(n>31)return 0;uint q=x>>n,mask=(1u<<n)-1u,r=x&mask,mid=1u<<(n-1);return q+uint(r>mid||(r==mid&&(q&1u)));}
DEV uint half_bits(float x){uint b=bits(x),a=b&0x7fffffffu,s=(b>>16)&0x8000u;int e=int(a>>23)-127;
 if(a>=0x7f800000u)return s|0x7c00u|((a&0x7fffffu)?0x200u:0u);
 if(e<-25)return s;
 if(e<-14)return s|shift_rne((a&0x7fffffu)|0x800000u,uint(-e-1));
 if(e>15)return s|0x7c00u;
 uint h=((a+0xfffu+((a>>13)&1u))>>13)-0x1c000u;return s|(h>=0x7c00u?0x7c00u:h);
}
DEV float from_half(uint h){uint s=(h&0x8000u)<<16,e=(h>>10)&31u,m=h&1023u;if(e==31)return value(s|0x7f800000u|(m<<13));if(!e){if(!m)return value(s);float f=float(m)*5.9604644775390625e-8f;return s?-f:f;}return value(s|((e+112)<<23)|(m<<13));}
#ifdef HIP_ISA_HALF
// Keep f32 expression evaluation and both rounding boundaries opaque to fusion.
DEV float H(float x){uint h;float result;asm("v_cvt_f16_f32 %0, %1" : "=v"(h) : "v"(x));asm("v_cvt_f32_f16 %0, %1" : "=v"(result) : "v"(h));return result;}
#else
DEV float H(float x){return from_half(half_bits(x));}
#endif
#ifndef HIP_NATIVE_FP8_F
#define HIP_NATIVE_FP8_F 1
#endif
#if HIP_NATIVE_FP8_F
DEV float F(float x){
 uint b=bits(x),a=b&0x7fffffffu;
 if(a==0)return 0.f;
 // Preserve the existing signed saturation, including nonfinite inputs.
 if(a>=0x43e00000u)return value((b&0x80000000u)|0x43e00000u);
 int packed=__builtin_amdgcn_cvt_pk_fp8_f32(x,0.f,0,false);
 return __builtin_amdgcn_cvt_f32_fp8(packed,0);
}
#else
DEV float F(float x){uint b=bits(x),a=b&0x7fffffffu,s=b&0x80000000u;if(a==0)return 0.f;
 if(a>=0x43e00000u)return value(s|0x43e00000u); // finite E4M3 saturation, including overflow
 if(a<0x3c800000u){float scaled=absf(x)*512.f;uint q=uint(scaled);float r=scaled-float(q);q+=uint(r>.5f||(r==.5f&&(q&1u)));float f=float(q)/512.f;return s?-f:f;}
 uint r=(a+0x7ffffu+((a>>20)&1u))&0xfff00000u;return value(s|(r>0x43e00000u?0x43e00000u:r));}
#endif

using f8=float __attribute__((ext_vector_type(8)));
using h8=_Float16 __attribute__((ext_vector_type(8)));
using i2=int __attribute__((ext_vector_type(2)));
#define WAVE KERNEL __attribute__((amdgpu_flat_work_group_size(32,32)))
DEV uint rc(){return __builtin_amdgcn_workitem_id_x()&15u;}
DEV uint gr(){return (__builtin_amdgcn_workitem_id_x()>>4)&1u;}
DEV uint bid(){return __builtin_amdgcn_workgroup_id_x();}
DEV void pack(i2&x,uint e,float v){uint b=uint(__builtin_amdgcn_cvt_pk_fp8_f32(clampf(v,-448.f,448.f),0.f,0,false))&255;x[e/4]=int(uint(x[e/4])|(b<<(8*(e%4))));}
template<bool ByteInput=false>
DEV f8 dot8(const float*in,const float*w,uint first,uint row,uint channels,uint begin,uint end,f8 a){
 for(uint k=begin;k<end;k+=16){i2 x{},y{};
  for(uint e=0;e<8;e++){uint j=k+gr()*8+e;if constexpr(!ByteInput)pack(x,e,in[(first+rc())*channels+j]);
#ifndef HIP_PREPACKED_WEIGHTS
   pack(y,e,w[(row+rc())*channels+j]);
#endif
  }
if constexpr(ByteInput){const uint*pi=reinterpret_cast<const uint*>(in);uint off=((first+rc())*channels+k+gr()*8)/4;x={int(pi[off]),int(pi[off+1])};}
#ifdef HIP_PREPACKED_WEIGHTS
  const uint*pw=reinterpret_cast<const uint*>(w);uint offset=((row+rc())*channels+k+gr()*8)/4;y={int(pw[offset]),int(pw[offset+1])};
#endif
  a=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(x,y,a);
 }return a;
}
#ifdef HIP_VIT_EXPAND_PAIR
// Two adjacent output tiles reuse each input load/FP8 pack. Keep the legacy
// launch ABI: odd column tiles return; even tiles own both output regions.
// Each accumulator retains the original increasing-K WMMA order.
WAVE void vit_expand(const float*in,const float*w,float*out,uint tokens,uint inputs,uint outputs){
 uint tile=bid()%(outputs/16),first=bid()/(outputs/16)*16,row=tile*16;
 if(first>=tokens||(tile&1u))return;
 bool second=row+16<outputs;f8 a{},b{};
 for(uint k=0;k<inputs;k+=16){
  i2 x{},y{},z{};
  for(uint e=0;e<8;e++){
   uint j=k+gr()*8+e;pack(x,e,in[(first+rc())*inputs+j]);
#ifndef HIP_PREPACKED_WEIGHTS
   pack(y,e,w[(row+rc())*inputs+j]);
   if(second)pack(z,e,w[(row+16+rc())*inputs+j]);
#endif
  }
#ifdef HIP_PREPACKED_WEIGHTS
  const uint*pw=reinterpret_cast<const uint*>(w);
  uint offset=((row+rc())*inputs+k+gr()*8)/4;
  y={int(pw[offset]),int(pw[offset+1])};
  if(second){offset+=16*inputs/4;z={int(pw[offset]),int(pw[offset+1])};}
#endif
  a=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(x,y,a);
  if(second)b=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(x,z,b);
 }
 for(uint e=0;e<8;e++){
  float v=a[e],g=clampf(v,-4.f,4.f),poly=__builtin_fmaf(g,absf(g)*(-.055908203125f)+.447265625f,.89453125f);
  out[(first+gr()*8+e)*outputs+row+rc()]=F(v*poly);
  if(second){v=b[e];g=clampf(v,-4.f,4.f);poly=__builtin_fmaf(g,absf(g)*(-.055908203125f)+.447265625f,.89453125f);
   out[(first+gr()*8+e)*outputs+row+16+rc()]=F(v*poly);}
 }
}
#else
WAVE void vit_expand(const float*in,const float*w,float*out,uint tokens,uint inputs,uint outputs){uint first=bid()/(outputs/16)*16,row=bid()%(outputs/16)*16;if(first>=tokens)return;f8 a{};a=dot8(in,w,first,row,inputs,0,inputs,a);for(uint e=0;e<8;e++){float v=a[e],g=clampf(v,-4.f,4.f),poly=__builtin_fmaf(g,absf(g)*(-.055908203125f)+.447265625f,.89453125f);out[(first+gr()*8+e)*outputs+row+rc()]=F(v*poly);}}
#endif
WAVE void vit_project(const float*in,const float*w,const float*skip,float*out,uint tokens,uint inputs,uint outputs){uint first=bid()/(outputs/16)*16,row=bid()%(outputs/16)*16;if(first>=tokens)return;f8 total{};
 if(inputs==4096){for(uint e=0;e<8;e++)total[e]=H(skip[(first+gr()*8+e)*outputs+row+rc()]*w[inputs*outputs+row+rc()]);for(uint p=0;p<4;p++){f8 a{};a=dot8(in,w,first,row,inputs,p*(inputs/4),(p+1)*(inputs/4),a);for(uint e=0;e<8;e++)total[e]+=a[e];}}
 else{for(uint p=0;p<4;p++){f8 a{};if(!p)for(uint e=0;e<8;e++)a[e]=H(skip[(first+gr()*8+e)*outputs+row+rc()]*w[inputs*outputs+row+rc()]);a=dot8(in,w,first,row,inputs,p*(inputs/4),(p+1)*(inputs/4),a);for(uint e=0;e<8;e++)total[e]=p?total[e]+a[e]:a[e];}}
 for(uint e=0;e<8;e++)out[(first+gr()*8+e)*outputs+row+rc()]=F(H(total[e]));
}
// Production fused QKV keeps F32 dot until square normalization; no two512 partition rounds.
WAVE void vit_qkv_project(const float*in,const float*w,float*out,uint tokens){uint perpart=(tokens/16)*64,part=bid()/perpart,local=bid()%perpart,first=local/64*16,row=local%64*16;if(part>=3)return;f8 a{};for(uint k=0;k<1024;k+=16){h8 x{},y{};for(uint e=0;e<8;e++){uint j=k+gr()*8+e;x[e]=(_Float16)in[(first+rc())*1024+j];y[e]=(_Float16)w[part*1048576+(row+rc())*1024+j];}a=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(x,y,a);}for(uint e=0;e<8;e++)out[(part*tokens+first+gr()*8+e)*1024+row+rc()]=a[e];}
WAVE void vit_qkv_normalize(const float*in,const float*w,float*out,uint tokens){uint perpart=(tokens/16)*64,part=bid()/perpart,local=bid()%perpart,first=local/64*16,row=local%64*16,head=row/32;if(part>=3)return;f8 sum{};if(part<2){for(uint k=0;k<32;k+=16){h8 x{},ones{};for(uint e=0;e<8;e++){uint j=head*32+k+gr()*8+e;float v=in[(part*tokens+first+rc())*1024+j];x[e]=(_Float16)(v*v);ones[e]=(_Float16)1.f;}sum=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(x,ones,sum);}}
 for(uint e=0;e<8;e++){uint i=(part*tokens+first+gr()*8+e)*1024+row+rc();float a=in[i];if(part<2){float scale=part==0?5.65625f*w[3145728+head]:1.f;a*=__builtin_amdgcn_rsqf(maxf(sum[e],6.198883056640625e-5f))*scale;}out[i]=F(a);}
}
// Explicit f32tof16 conversion in production attention is RTZ, unlike Matrix.Cast<F16>.
#ifndef HIP_NATIVE_RTZ
#define HIP_NATIVE_RTZ 1
#endif
#if HIP_NATIVE_RTZ
DEV float Hrtz(float x){uint h;float r;asm("v_cvt_pkrtz_f16_f32 %0, %1, %1":"=v"(h):"v"(x));asm("v_cvt_f32_f16 %0, %1":"=v"(r):"v"(h));return r;}
#else
DEV float Hrtz(float x){uint b=bits(x),a=b&0x7fffffffu,s=(b>>16)&0x8000u;int e=int(a>>23)-127;if(a>=0x7f800000u)return from_half(s|0x7c00u|((a&0x7fffffu)?0x200u:0u));if(e>15)return from_half(s|0x7bffu);if(e<-24)return from_half(s);if(e<-14)return from_half(s|(((a&0x7fffffu)|0x800000u)>>uint(-e-1)));return from_half(s|((a>>13)-0x1c000u));}
#endif
// scores work=T*T*32; T%16=0; ex[query][head32][key].
WAVE void vit_attention_scores_fast(const float*in,float*out,uint tokens){uint kt= tokens/16,key=(bid()%kt)*16,head=(bid()/kt)%32,first=bid()/(kt*32)*16;if(first>=tokens)return;f8 a{};for(uint k=0;k<32;k+=16){i2 x{},y{};for(uint e=0;e<8;e++){uint j=k+gr()*8+e;pack(x,e,in[(first+rc())*1024+head*32+j]);pack(y,e,in[(tokens+key+rc())*1024+head*32+j]);}a=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(x,y,a);}for(uint e=0;e<8;e++){float af=clampf(a[e]*from_half(0x2dbb)+1.708984375f,1.439453125f,1.9775390625f);uint hb=(bits(af)>>13)-0x1c000u;out[((first+gr()*8+e)*32+head)*tokens+key+rc()]=from_half(((hb<<4)+0x4000u)&65535u);}}
// inverse SPECIAL work=T*32*16, not T*32. One wave handles16 queries for one head.
WAVE void vit_attention_inverse_fast(const float*ex,float*out,uint tokens){uint head=bid()%32,first=bid()/32*16;if(first>=tokens)return;f8 a{};for(uint k=0;k<tokens;k+=16){h8 x{},ones{};for(uint e=0;e<8;e++){uint key=k+gr()*8+e;x[e]=(_Float16)ex[((first+rc())*32+head)*tokens+key];ones[e]=(_Float16)1.f;}a=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(x,ones,a);}if(rc()==0)for(uint e=0;e<8;e++)out[(first+gr()*8+e)*32+head]=1.f/a[e];}
// FUSED ViT attention (host option vit_attn_fused): one wave = 16 queries x one head over every key, bid = query tile*32 + head.
// Same per-element operations, operand packing and MMA K order as vit_attention_scores_fast / vit_attention_inverse_fast /
// vit_attention_av_fast: Q packed once, scores per16-key tile through the same exp bit map, the half bit pattern those
// kernels exchange through the f32 ex tensor kept in LDS ([query16][key] uint16, exact: ex is an f32 copy of a half),
// denominator = f16 MMA of the LDS rows against ones (K16 steps in key order), PV = FP8 MMA of pack(ex) against V for
// both16-column halves of the head, epilogue F(Hrtz(acc*inv)). Requires tokens%16==0 and tokens<=640.
// LDS per wave: P as E4M3 bytes [16][MAXT+16] plus a double-buffered16x16 half tile that transposes each score tile from
// accumulator layout to the A-operand layout (keys along K) for the denominator MMA and the byte store. Three token
// buckets keep the static LDS (and so the occupancy) matched to the geometry: 256 (8.2KB), 400 (8.2KB), 640 (12KB).
// ByteInput: Q/K/V arrive as the E4M3 bytes vit_qkv_project_normalize_fused_f16compact_fp8 stores (byte_F of the same
// F() values the f32 tensor holds, so pack() of the f32 value and the stored byte are identical): Q/K rows are one
// 8-byte load per lane, V columns eight byte loads placed exactly as pack() places them.
template<uint MAXT,bool ByteInput=false>
DEV void vit_attention_fused_body(const float*in,float*out,uint tokens){
 uint head=bid()%32,first=bid()/32*16;if(first>=tokens)return;
 __attribute__((shared)) unsigned char p8[16*(MAXT+16)];
 __attribute__((shared)) unsigned short t16[2*16*24];
 const uint S=tokens+16;const unsigned char*in8=reinterpret_cast<const unsigned char*>(in);
 i2 q[2]{};for(uint k=0;k<32;k+=16){if constexpr(ByteInput)__builtin_memcpy(&q[k/16],in8+(first+rc())*1024+head*32+k+gr()*8,8);else for(uint e=0;e<8;e++){uint j=k+gr()*8+e;pack(q[k/16],e,in[(first+rc())*1024+head*32+j]);}}
 h8 ones{};for(uint e=0;e<8;e++)ones[e]=(_Float16)1.f;
 f8 sum{};
 for(uint key=0,tile=0;key<tokens;key+=16,tile^=1u){f8 a{};
  for(uint k=0;k<32;k+=16){i2 y{};if constexpr(ByteInput)__builtin_memcpy(&y,in8+(tokens+key+rc())*1024+head*32+k+gr()*8,8);else for(uint e=0;e<8;e++){uint j=k+gr()*8+e;pack(y,e,in[(tokens+key+rc())*1024+head*32+j]);}a=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(q[k/16],y,a);}
  unsigned short*t=t16+tile*16*24;
  for(uint e=0;e<8;e++){float af=clampf(a[e]*from_half(0x2dbb)+1.708984375f,1.439453125f,1.9775390625f);uint hb=(bits(af)>>13)-0x1c000u;t[(gr()*8+e)*24+rc()]=(unsigned short)(((hb<<4)+0x4000u)&65535u);}
  __builtin_amdgcn_fence(3,"workgroup");__builtin_amdgcn_s_barrier();__builtin_amdgcn_fence(2,"workgroup");
  h8 x{};i2 xb{};for(uint e=0;e<8;e++){unsigned short u=t[rc()*24+gr()*8+e];union{unsigned short u;_Float16 h;}cv;cv.u=u;x[e]=cv.h;pack(xb,e,from_half(u));}
  sum=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(x,ones,sum);
  __builtin_memcpy(p8+rc()*S+key+gr()*8,&xb,8);
 }
 float inv[8];for(uint e=0;e<8;e++)inv[e]=1.f/sum[e];
 __builtin_amdgcn_fence(3,"workgroup");__builtin_amdgcn_s_barrier();__builtin_amdgcn_fence(2,"workgroup");
 f8 acc[2]{};
 for(uint k=0;k<tokens;k+=16){i2 x;__builtin_memcpy(&x,p8+rc()*S+k+gr()*8,8);
  for(uint c=0;c<2;c++){i2 y{};for(uint e=0;e<8;e++){uint key=k+gr()*8+e;if constexpr(ByteInput){uint b=in8[(2*tokens+key)*1024+head*32+c*16+rc()];y[e/4]=int(uint(y[e/4])|(b<<(8*(e%4))));}else pack(y,e,in[(2*tokens+key)*1024+head*32+c*16+rc()]);}acc[c]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(x,y,acc[c]);}
 }
 for(uint c=0;c<2;c++)for(uint e=0;e<8;e++)out[(first+gr()*8+e)*1024+head*32+c*16+rc()]=F(Hrtz(acc[c][e]*inv[e]));
}
WAVE void vit_attention_fused_256(const float*in,float*out,uint tokens){vit_attention_fused_body<256>(in,out,tokens);}
WAVE void vit_attention_fused_400(const float*in,float*out,uint tokens){vit_attention_fused_body<400>(in,out,tokens);}
WAVE void vit_attention_fused_640(const float*in,float*out,uint tokens){vit_attention_fused_body<640>(in,out,tokens);}
WAVE void vit_attention_fused_256_bytein(const float*in,float*out,uint tokens){vit_attention_fused_body<256,true>(in,out,tokens);}
WAVE void vit_attention_fused_400_bytein(const float*in,float*out,uint tokens){vit_attention_fused_body<400,true>(in,out,tokens);}
WAVE void vit_attention_fused_640_bytein(const float*in,float*out,uint tokens){vit_attention_fused_body<640,true>(in,out,tokens);}
WAVE void vit_attention_av_fast(const float*in,const float*ex,const float*inv,float*out,uint tokens){uint first=bid()/64*16,head=(bid()%64)/2,col=(bid()%2)*16;if(first>=tokens)return;f8 a{};for(uint k=0;k<tokens;k+=16){i2 x{},y{};for(uint e=0;e<8;e++){uint key=k+gr()*8+e;pack(x,e,ex[((first+rc())*32+head)*tokens+key]);pack(y,e,in[(2*tokens+key)*1024+head*32+col+rc()]);}a=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(x,y,a);}for(uint e=0;e<8;e++){uint q=first+gr()*8+e;out[q*1024+head*32+col+rc()]=F(Hrtz(a[e]*inv[q*32+head]));}}
// Production decoder build leaves NATIVE_DECODER_HW_H=0: H is integer RNE.
WAVE void decoder_project2x(const float*in,const float*w,const float*skip,float*out,uint iw,uint ih,uint ow,uint oh,uint inputs,uint outputs){uint first=bid()/(outputs/16)*16,row=bid()%(outputs/16)*16;if(first>=iw*ih)return;uint parts=inputs==1024?4:1;f8 total{};for(uint p=0;p<parts;p++){f8 a{};for(uint k=p*(inputs/parts);k<(p+1)*(inputs/parts);k+=16){h8 x{},y{};for(uint e=0;e<8;e++){uint j=k+gr()*8+e;x[e]=(_Float16)in[(first+rc())*inputs+j];y[e]=(_Float16)w[(row+rc())*inputs+j];}a=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(x,y,a);}for(uint e=0;e<8;e++)total[e]=p?total[e]+a[e]:a[e];}for(uint e=0;e<8;e++){uint token=first+gr()*8+e;float t=H(total[e]);for(uint dy=0;dy<2;dy++)for(uint dx=0;dx<2;dx++){uint x=(token%iw)*2+dx,y=(token/iw)*2+dy;if(x>=ow||y>=oh)continue;uint i=(y*ow+x)*outputs+row+rc();float merged=H(t+F(skip[i])*w[inputs*outputs+row+rc()]);out[i]=outputs==32?merged:F(merged);}}}
template<bool ByteInput=false>
DEV f8 dot16(const float*in,const float*w,uint first,uint row,uint instride,uint kcols,uint inoff,uint woff,f8 a){for(uint k=0;k<kcols;k+=16){h8 x{},y{};for(uint e=0;e<8;e++){uint j=k+gr()*8+e;if constexpr(ByteInput)x[e]=(_Float16)__builtin_amdgcn_cvt_f32_fp8(int(reinterpret_cast<const unsigned char*>(in)[(first+rc())*instride+inoff+j]),0);else x[e]=(_Float16)in[(first+rc())*instride+inoff+j];y[e]=(_Float16)w[woff+(row+rc())*kcols+j];}a=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(x,y,a);}return a;}
WAVE void split_mix(const float*in,const float*w,float*out,uint tokens){uint first=bid()/32*16,row=bid()%32*16;if(first>=tokens)return;f8 a{};a=dot16(in,w,first,row,512,512,0,0,a);for(uint e=0;e<8;e++)out[(first+gr()*8+e)*512+row+rc()]=F(Hrtz(a[e]));}
WAVE void split_expand(const float*in,const float*w,float*out,uint tokens){uint first=bid()/128*16,col=bid()%128*16,g=col/256,row=col%256;if(first>=tokens)return;f8 a{};a=dot16(in,w,first,row,512,64,g*64,262144+g*16384,a);for(uint e=0;e<8;e++){float v=Hrtz(a[e]),gate=clampf(v,-4.f,4.f),poly=gate*(absf(gate)*(-.055908203125f)+.447265625f)+.89453125f;out[(first+gr()*8+e)*2048+col+rc()]=F(v*poly);}}
WAVE void split_contract(const float*in,const float*w,float*out,uint tokens){uint first=bid()/32*16,col=bid()%32*16,g=col/64,row=col%64;if(first>=tokens)return;f8 a{};a=dot16(in,w,first,row,2048,256,g*256,393216+g*16384,a);for(uint e=0;e<8;e++)out[(first+gr()*8+e)*512+col+rc()]=F(Hrtz(a[e]));}
// stream0 FFWD projection build omits NATIVE_HW_H: initial and final H are integer RNE.
WAVE void split_projection(const float*in,const float*w,const float*skip,float*out,uint tokens){uint first=bid()/32*16,row=bid()%32*16;if(first>=tokens)return;f8 a{};for(uint e=0;e<8;e++)a[e]=H(skip[(first+gr()*8+e)*512+row+rc()]*w[262144+row+rc()]);a=dot8(in,w,first,row,512,0,512,a);for(uint e=0;e<8;e++)out[(first+gr()*8+e)*512+row+rc()]=F(H(a[e]));}

DEV unsigned char byte_F(float x){return static_cast<unsigned char>(__builtin_amdgcn_cvt_pk_fp8_f32(F(x),0.f,0,false));}

WAVE void vit_expand_fp8(const float*in,const float*w,float*out,uint tokens,uint inputs,uint outputs){uint first=bid()/(outputs/16)*16,row=bid()%(outputs/16)*16;if(first>=tokens)return;f8 a{};a=dot8(in,w,first,row,inputs,0,inputs,a);for(uint e=0;e<8;e++){float v=a[e],g=clampf(v,-4.f,4.f),poly=__builtin_fmaf(g,absf(g)*(-.055908203125f)+.447265625f,.89453125f);reinterpret_cast<unsigned char*>(out)[(first+gr()*8+e)*outputs+row+rc()]=byte_F(v*poly);}}

WAVE void vit_project_fp8(const float*in,const float*w,const float*skip,float*out,uint tokens,uint inputs,uint outputs){uint first=bid()/(outputs/16)*16,row=bid()%(outputs/16)*16;if(first>=tokens)return;f8 total{};
 if(inputs==4096){for(uint e=0;e<8;e++)total[e]=H(skip[(first+gr()*8+e)*outputs+row+rc()]*w[inputs*outputs+row+rc()]);for(uint p=0;p<4;p++){f8 a{};a=dot8<true>(in,w,first,row,inputs,p*(inputs/4),(p+1)*(inputs/4),a);for(uint e=0;e<8;e++)total[e]+=a[e];}}
 else{for(uint p=0;p<4;p++){f8 a{};if(!p)for(uint e=0;e<8;e++)a[e]=H(skip[(first+gr()*8+e)*outputs+row+rc()]*w[inputs*outputs+row+rc()]);a=dot8<true>(in,w,first,row,inputs,p*(inputs/4),(p+1)*(inputs/4),a);for(uint e=0;e<8;e++)total[e]=p?total[e]+a[e]:a[e];}}
 for(uint e=0;e<8;e++)out[(first+gr()*8+e)*outputs+row+rc()]=F(H(total[e]));
}

WAVE void split_expand_fp8(const float*in,const float*w,float*out,uint tokens){uint first=bid()/128*16,col=bid()%128*16,g=col/256,row=col%256;if(first>=tokens)return;f8 a{};a=dot16(in,w,first,row,512,64,g*64,262144+g*16384,a);for(uint e=0;e<8;e++){float v=Hrtz(a[e]),gate=clampf(v,-4.f,4.f),poly=gate*(absf(gate)*(-.055908203125f)+.447265625f)+.89453125f;reinterpret_cast<unsigned char*>(out)[(first+gr()*8+e)*2048+col+rc()]=byte_F(v*poly);}}

WAVE void split_contract_fp8(const float*in,const float*w,float*out,uint tokens){uint first=bid()/32*16,col=bid()%32*16,g=col/64,row=col%64;if(first>=tokens)return;f8 a{};a=dot16<true>(in,w,first,row,2048,256,g*256,393216+g*16384,a);for(uint e=0;e<8;e++)out[(first+gr()*8+e)*512+col+rc()]=F(Hrtz(a[e]));}

// Four independent K1024 partitions of the existing K4096 contract.
WAVE void vit_contract_parts_fp8(const float*in,const float*w,float*out,uint tokens){
 uint blocks=(tokens/16)*64,part=bid()/blocks,local=bid()%blocks,first=local/64*16,row=local%64*16;
 if(part>=4)return;f8 a{};a=dot8<true>(in,w,first,row,4096,part*1024,(part+1)*1024,a);
 for(uint e=0;e<8;e++)out[(part*tokens+first+gr()*8+e)*1024+row+rc()]=a[e];
}
KERNEL __attribute__((amdgpu_flat_work_group_size(256,256)))
void vit_contract_combine(const float*partial,const float*w,const float*skip,float*out,uint tokens){
 uint i=bid()*256+__builtin_amdgcn_workitem_id_x(),count=tokens*1024;if(i>=count)return;
 float total=H(skip[i]*w[4194304+i%1024]);
 for(uint part=0;part<4;part++)total+=partial[part*count+i];
 out[i]=F(H(total));
}

template<bool Tiled> DEV i2 vit_weight_fragment(const float*w,uint row,uint channels,uint k){
 i2 b{};
 if constexpr(Tiled){const unsigned char*p=reinterpret_cast<const unsigned char*>(w);uint off=((row/16)*(channels/32)+k/32)*512+(k%32+gr()*8)*16+row%16;for(uint e=0;e<8;e++)b[e/4]=int(uint(b[e/4])|(uint(p[off+16*e])<<(8*(e%4))));}
 else{const uint*p=reinterpret_cast<const uint*>(w);uint off=(row*channels+k+gr()*8)/4;b={int(p[off]),int(p[off+1])};}
 return b;
}
KERNEL __attribute__((amdgpu_flat_work_group_size(256,256)))
void vit_pack_input(const float*in,uint*out,uint count){
 uint word=bid()*256+__builtin_amdgcn_workitem_id_x(),i=word*4;if(i>=count)return;
 uint a=uint(__builtin_amdgcn_cvt_pk_fp8_f32(clampf(in[i],-448.f,448.f),clampf(in[i+1],-448.f,448.f),0,false));
 uint b=uint(__builtin_amdgcn_cvt_pk_fp8_f32(clampf(in[i+2],-448.f,448.f),clampf(in[i+3],-448.f,448.f),0,false));
 out[word]=(a&65535u)|((b&65535u)<<16);
}
// One wave produces16x64, reusing A across four output-column fragments.
DEV i2 vit_weight_fragment_native(const float*w,uint row,uint channels,uint k){i2 b;__builtin_memcpy(&b,reinterpret_cast<const unsigned char*>(w)+((row/16)*(channels/32)+k/32)*512+(((k%32)/16*2+gr())*16+row%16)*8,8);return b;}
template<bool Tiled=false,bool ByteInput=false,bool Frag=false>
DEV void vit_expand_blocked_body(const float*in,const float*w,float*out,uint tokens,uint inputs,uint outputs){
 uint tiles=outputs/64,first=bid()/tiles*16,col=bid()%tiles*64;if(first>=tokens)return;
 const uint*pw=reinterpret_cast<const uint*>(w);f8 accum[4]{};
 for(uint k=0;k<inputs;k+=16){i2 a{};
  if constexpr(ByteInput){const uint*p=reinterpret_cast<const uint*>(in);uint off=((first+rc())*inputs+k+gr()*8)/4;a={int(p[off]),int(p[off+1])};}
  else for(uint e=0;e<8;e++)pack(a,e,in[(first+rc())*inputs+k+gr()*8+e]);
  for(uint n=0;n<4;n++){uint row=col+n*16+rc();i2 b;if constexpr(Frag)b=vit_weight_fragment_native(w,row,inputs,k);else b=vit_weight_fragment<Tiled>(w,row,inputs,k);accum[n]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,accum[n]);}
 }
 for(uint n=0;n<4;n++)for(uint e=0;e<8;e++){float v=accum[n][e],g=clampf(v,-4.f,4.f),poly=__builtin_fmaf(g,absf(g)*(-.055908203125f)+.447265625f,.89453125f);reinterpret_cast<unsigned char*>(out)[(first+gr()*8+e)*outputs+col+n*16+rc()]=byte_F(v*poly);}
}

// BM token tiles per wave (host option vit_expand_m4, HLSL BLOCK_M=4 shape): every weight fragment load serves BM
// token tiles. Each accumulator keeps its own K-ascending order with the same a/b operands as the single-tile body, so
// the bytes are identical; token tiles past the end are neither loaded nor stored (wave-uniform branch).
template<bool Tiled,bool ByteInput,uint BM,bool Frag=false>
DEV void vit_expand_blocked_body_m(const float*in,const float*w,float*out,uint tokens,uint inputs,uint outputs){
 uint tiles=outputs/64,first=bid()/tiles*16*BM,col=bid()%tiles*64;if(first>=tokens)return;
 f8 accum[BM][4]{};
 for(uint k=0;k<inputs;k+=16){i2 a[BM];
  #pragma unroll
  for(uint m=0;m<BM;m++){a[m]={};uint row=first+m*16;if(row<tokens){if constexpr(ByteInput){const uint*p=reinterpret_cast<const uint*>(in);uint off=((row+rc())*inputs+k+gr()*8)/4;a[m]={int(p[off]),int(p[off+1])};}else for(uint e=0;e<8;e++)pack(a[m],e,in[(row+rc())*inputs+k+gr()*8+e]);}}
  i2 b[4];
  #pragma unroll
  for(uint n=0;n<4;n++){if constexpr(Frag)b[n]=vit_weight_fragment_native(w,col+n*16+rc(),inputs,k);else b[n]=vit_weight_fragment<Tiled>(w,col+n*16+rc(),inputs,k);}
  #pragma unroll
  for(uint m=0;m<BM;m++){if(first+m*16<tokens){
   #pragma unroll
   for(uint n=0;n<4;n++)accum[m][n]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a[m],b[n],accum[m][n]);}}
 }
 #pragma unroll
 for(uint m=0;m<BM;m++){uint row=first+m*16;if(row<tokens){
  #pragma unroll
  for(uint n=0;n<4;n++)for(uint e=0;e<8;e++){float v=accum[m][n][e],g=clampf(v,-4.f,4.f),poly=__builtin_fmaf(g,absf(g)*(-.055908203125f)+.447265625f,.89453125f);reinterpret_cast<unsigned char*>(out)[(row+gr()*8+e)*outputs+col+n*16+rc()]=byte_F(v*poly);}}}
}
WAVE void vit_expand_blocked_fp8_tiled_bytein_m4(const float*in,const float*w,float*out,uint tokens,uint inputs,uint outputs){vit_expand_blocked_body_m<true,true,4>(in,w,out,tokens,inputs,outputs);}
WAVE void vit_expand_blocked_fp8_frag_bytein_m4(const float*in,const float*w,float*out,uint tokens,uint inputs,uint outputs){vit_expand_blocked_body_m<true,true,4,true>(in,w,out,tokens,inputs,outputs);}

template<bool Partial,bool Tiled=false>
DEV void vit_contract_blocked_body(const float*in,const float*w,const float*skip,float*out,uint tokens){
 uint blocks=tokens,part0=Partial?bid()/blocks:0,local=Partial?bid()%blocks:bid(),first=local/16*16,col=local%16*64;
 if(first>=tokens||part0>=4)return;const uint*ip=reinterpret_cast<const uint*>(in),*wp=reinterpret_cast<const uint*>(w);f8 total[4]{};
 if constexpr(!Partial)for(uint n=0;n<4;n++)for(uint e=0;e<8;e++){uint c=col+n*16+rc();total[n][e]=H(skip[(first+gr()*8+e)*1024+c]*w[4194304+c]);}
 for(uint part=part0;part<(Partial?part0+1:4);part++){f8 acc[4]{};
  for(uint k=part*1024;k<(part+1)*1024;k+=16){uint off=((first+rc())*4096+k+gr()*8)/4;i2 a={int(ip[off]),int(ip[off+1])};
   for(uint n=0;n<4;n++){uint row=col+n*16+rc(),wo=(row*4096+k+gr()*8)/4;i2 b=vit_weight_fragment<Tiled>(w,row,4096,k);acc[n]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,acc[n]);}
  }
  for(uint n=0;n<4;n++)for(uint e=0;e<8;e++){if constexpr(Partial)out[(part*tokens+first+gr()*8+e)*1024+col+n*16+rc()]=acc[n][e];else total[n][e]+=acc[n][e];}
 }
 if constexpr(!Partial)for(uint n=0;n<4;n++)for(uint e=0;e<8;e++)out[(first+gr()*8+e)*1024+col+n*16+rc()]=F(H(total[n][e]));
}
WAVE void vit_contract_blocked_fp8(const float*in,const float*w,const float*skip,float*out,uint tokens,uint inputs,uint outputs){if(inputs==4096&&outputs==1024)vit_contract_blocked_body<false>(in,w,skip,out,tokens);}
WAVE void vit_contract_parts_blocked_fp8(const float*in,const float*w,float*out,uint tokens){vit_contract_blocked_body<true>(in,w,nullptr,out,tokens);}

WAVE void vit_expand_blocked_fp8(const float*in,const float*w,float*out,uint tokens,uint inputs,uint outputs){vit_expand_blocked_body<false,false>(in,w,out,tokens,inputs,outputs);}

WAVE void vit_expand_blocked_fp8_tiled(const float*in,const float*w,float*out,uint tokens,uint inputs,uint outputs){vit_expand_blocked_body<true,false>(in,w,out,tokens,inputs,outputs);}

WAVE void vit_expand_blocked_fp8_bytein(const float*in,const float*w,float*out,uint tokens,uint inputs,uint outputs){vit_expand_blocked_body<false,true>(in,w,out,tokens,inputs,outputs);}

WAVE void vit_expand_blocked_fp8_tiled_bytein(const float*in,const float*w,float*out,uint tokens,uint inputs,uint outputs){vit_expand_blocked_body<true,true>(in,w,out,tokens,inputs,outputs);}
// Fragment-native weight layout (FragmentPackedMatrix): one 8-byte load per B fragment instead of eight byte gathers.
WAVE void vit_expand_blocked_fp8_frag_bytein(const float*in,const float*w,float*out,uint tokens,uint inputs,uint outputs){vit_expand_blocked_body<true,true,true>(in,w,out,tokens,inputs,outputs);}

WAVE void vit_contract_blocked_fp8_tiled(const float*in,const float*w,const float*skip,float*out,uint tokens,uint inputs,uint outputs){if(inputs==4096&&outputs==1024)vit_contract_blocked_body<false,true>(in,w,skip,out,tokens);}
WAVE void vit_contract_parts_blocked_fp8_tiled(const float*in,const float*w,float*out,uint tokens){vit_contract_blocked_body<true,true>(in,w,nullptr,out,tokens);}

KERNEL __attribute__((amdgpu_flat_work_group_size(128,128)))
void split_ffn_fused(const float*in,const float*w,float*out,uint tokens){
 uint block=bid(),first=(block/8)*16,g=block%8,tid=__builtin_amdgcn_workitem_id_x(),wave=tid/32;
 if(first>=tokens)return;
 __attribute__((shared)) unsigned char hidden[16*260];
 f8 expanded[4]{};
 for(uint j=0;j<4;j++)expanded[j]=dot16(in,w,first,wave*64+j*16,512,64,g*64,262144+g*16384,expanded[j]);
 for(uint j=0;j<4;j++)for(uint e=0;e<8;e++){float v=Hrtz(expanded[j][e]),gate=clampf(v,-4.f,4.f),poly=gate*(absf(gate)*(-.055908203125f)+.447265625f)+.89453125f;hidden[(gr()*8+e)*260+wave*64+j*16+rc()]=byte_F(v*poly);}
 __builtin_amdgcn_s_barrier();
 f8 result{};
 for(uint k=0;k<256;k+=16){h8 a{},b{};for(uint e=0;e<8;e++){uint kk=k+gr()*8+e;a[e]=(_Float16)__builtin_amdgcn_cvt_f32_fp8(int(hidden[rc()*260+kk]),0);b[e]=(_Float16)w[393216+g*16384+(wave*16+rc())*256+kk];}result=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(a,b,result);}
 for(uint e=0;e<8;e++)out[(first+gr()*8+e)*512+g*64+wave*16+rc()]=F(Hrtz(result[e]));
}

WAVE void split_mix_blocked(const float*in,const float*w,float*out,uint tokens){
 uint first=bid()/8*16,row=bid()%8*64;if(first>=tokens)return;f8 acc[4]{};
 for(uint k=0;k<512;k+=16){h8 a{};for(uint e=0;e<8;e++)a[e]=(_Float16)in[(first+rc())*512+k+gr()*8+e];for(uint j=0;j<4;j++){h8 b{};for(uint e=0;e<8;e++)b[e]=(_Float16)w[(row+j*16+rc())*512+k+gr()*8+e];acc[j]=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(a,b,acc[j]);}}
 for(uint j=0;j<4;j++)for(uint e=0;e<8;e++)out[(first+gr()*8+e)*512+row+j*16+rc()]=F(Hrtz(acc[j][e]));
}

WAVE void split_projection_blocked(const float*in,const float*w,const float*skip,float*out,uint tokens){
 uint first=bid()/8*16,row=bid()%8*64;if(first>=tokens)return;f8 acc[4]{};
 for(uint j=0;j<4;j++)for(uint e=0;e<8;e++)acc[j][e]=H(skip[(first+gr()*8+e)*512+row+j*16+rc()]*w[262144+row+j*16+rc()]);
 for(uint k=0;k<512;k+=16){i2 a{};for(uint e=0;e<8;e++)pack(a,e,in[(first+rc())*512+k+gr()*8+e]);for(uint j=0;j<4;j++){i2 b{};
#ifdef HIP_PREPACKED_WEIGHTS
  const uint*pw=reinterpret_cast<const uint*>(w);uint off=((row+j*16+rc())*512+k+gr()*8)/4;b={int(pw[off]),int(pw[off+1])};
#else
  for(uint e=0;e<8;e++)pack(b,e,w[(row+j*16+rc())*512+k+gr()*8+e]);
#endif
  acc[j]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,acc[j]);}}
 for(uint j=0;j<4;j++)for(uint e=0;e<8;e++)out[(first+gr()*8+e)*512+row+j*16+rc()]=F(H(acc[j][e]));
}

WAVE void vit_qkv_project_blocked(const float*in,const float*w,float*out,uint tokens){
 uint perpart=(tokens/16)*32,part=bid()/perpart,local=bid()%perpart,first=local/32*16,row=local%32*32;if(part>=3)return;f8 acc[2]{};
 for(uint k=0;k<1024;k+=16){h8 a{};for(uint e=0;e<8;e++)a[e]=(_Float16)in[(first+rc())*1024+k+gr()*8+e];for(uint j=0;j<2;j++){h8 b{};for(uint e=0;e<8;e++)b[e]=(_Float16)w[part*1048576+(row+j*16+rc())*1024+k+gr()*8+e];acc[j]=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(a,b,acc[j]);}}
 for(uint j=0;j<2;j++)for(uint e=0;e<8;e++)out[(part*tokens+first+gr()*8+e)*1024+row+j*16+rc()]=acc[j][e];
}

WAVE void vit_qkv_project_normalize_fused(const float*in,const float*w,float*out,uint tokens){
 uint perpart=(tokens/16)*32,part=bid()/perpart,local=bid()%perpart,first=local/32*16,row=local%32*32;if(part>=3)return;f8 acc[2]{};
 for(uint k=0;k<1024;k+=16){h8 a{};for(uint e=0;e<8;e++)a[e]=(_Float16)in[(first+rc())*1024+k+gr()*8+e];for(uint j=0;j<2;j++){h8 b{};for(uint e=0;e<8;e++)b[e]=(_Float16)w[part*1048576+(row+j*16+rc())*1024+k+gr()*8+e];acc[j]=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(a,b,acc[j]);}}
 __attribute__((shared)) float raw[16*33];
 f8 sum{};
 if(part<2){
  for(uint j=0;j<2;j++)for(uint e=0;e<8;e++)raw[(gr()*8+e)*33+j*16+rc()]=acc[j][e];
  __builtin_amdgcn_s_barrier();
  for(uint k=0;k<32;k+=16){h8 x{},ones{};for(uint e=0;e<8;e++){float v=raw[rc()*33+k+gr()*8+e];x[e]=(_Float16)(v*v);ones[e]=(_Float16)1.f;}sum=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(x,ones,sum);}
 }
 for(uint j=0;j<2;j++)for(uint e=0;e<8;e++){float v=acc[j][e];if(part<2){float scale=part==0?5.65625f*w[3145728+row/32]:1.f;v*=__builtin_amdgcn_rsqf(maxf(sum[e],6.198883056640625e-5f))*scale;}out[(part*tokens+first+gr()*8+e)*1024+row+j*16+rc()]=F(v);}
}

KERNEL __attribute__((amdgpu_flat_work_group_size(128,128)))
// Keep expansion F16: the FP8 expansion probe differs on block46 wide-range input.
void split_ffn_fused_fp8(const float*in,const float*w,float*out,uint tokens){
 uint block=bid(),first=(block/8)*16,g=block%8,tid=__builtin_amdgcn_workitem_id_x(),wave=tid/32;
 if(first>=tokens)return;
 __attribute__((shared)) unsigned char hidden[16*260];
 f8 expanded[4]{};
 for(uint j=0;j<4;j++)for(uint k=0;k<64;k+=16){h8 a{},b{};for(uint e=0;e<8;e++)a[e]=(_Float16)in[(first+rc())*512+g*64+k+gr()*8+e];__builtin_memcpy(&b,reinterpret_cast<const _Float16*>(w+262144)+g*16384+(wave*64+j*16+rc())*64+k+gr()*8,16);expanded[j]=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(a,b,expanded[j]);}
 for(uint j=0;j<4;j++)for(uint e=0;e<8;e++){float v=Hrtz(expanded[j][e]),gate=clampf(v,-4.f,4.f),poly=gate*(absf(gate)*(-.055908203125f)+.447265625f)+.89453125f;hidden[(gr()*8+e)*260+wave*64+j*16+rc()]=byte_F(v*poly);}
 __builtin_amdgcn_s_barrier();
 f8 result{};
 const uint*pw=reinterpret_cast<const uint*>(w);
 for(uint k=0;k<256;k+=16){i2 a{};__builtin_memcpy(&a,hidden+rc()*260+k+gr()*8,8);uint off=393216+g*4096+((wave*16+rc())*256+k+gr()*8)/4;i2 b={int(pw[off]),int(pw[off+1])};result=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,result);}
 for(uint e=0;e<8;e++)out[(first+gr()*8+e)*512+g*64+wave*16+rc()]=F(Hrtz(result[e]));
}

WAVE void vit_qkv_project_normalize_fused_f16weight(const float*in,const float*w,float*out,uint tokens){
 uint perpart=(tokens/16)*32,part=bid()/perpart,local=bid()%perpart,first=local/32*16,row=local%32*32;if(part>=3)return;f8 acc[2]{};
 for(uint k=0;k<1024;k+=16){h8 a{};for(uint e=0;e<8;e++)a[e]=(_Float16)in[(first+rc())*1024+k+gr()*8+e];for(uint j=0;j<2;j++){h8 b{};__builtin_memcpy(&b,reinterpret_cast<const _Float16*>(w)+part*1048576+(row+j*16+rc())*1024+k+gr()*8,16);acc[j]=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(a,b,acc[j]);}}
 __attribute__((shared)) float raw[16*33];
 f8 sum{};
 if(part<2){
  for(uint j=0;j<2;j++)for(uint e=0;e<8;e++)raw[(gr()*8+e)*33+j*16+rc()]=acc[j][e];
  __builtin_amdgcn_s_barrier();
  for(uint k=0;k<32;k+=16){h8 x{},ones{};for(uint e=0;e<8;e++){float v=raw[rc()*33+k+gr()*8+e];x[e]=(_Float16)(v*v);ones[e]=(_Float16)1.f;}sum=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(x,ones,sum);}
 }
 for(uint j=0;j<2;j++)for(uint e=0;e<8;e++){float v=acc[j][e];if(part<2){float scale=part==0?5.65625f*w[3145728+row/32]:1.f;v*=__builtin_amdgcn_rsqf(maxf(sum[e],6.198883056640625e-5f))*scale;}out[(part*tokens+first+gr()*8+e)*1024+row+j*16+rc()]=F(v);}
}

// Byte-output twin of vit_qkv_project_normalize_fused_f16compact: identical projection/normalize, the F() result stored
// as its E4M3 byte (byte_F: exact on the F() lattice, same byte pack() would produce from the f32 value).
WAVE void vit_qkv_project_normalize_fused_f16compact_fp8(const float*in,const float*w,unsigned char*out,uint tokens){
 uint perpart=(tokens/16)*32,part=bid()/perpart,local=bid()%perpart,first=local/32*16,row=local%32*32;if(part>=3)return;f8 acc[2]{};
 for(uint k=0;k<1024;k+=16){h8 a{};for(uint e=0;e<8;e++)a[e]=(_Float16)in[(first+rc())*1024+k+gr()*8+e];for(uint j=0;j<2;j++){h8 b{};__builtin_memcpy(&b,reinterpret_cast<const _Float16*>(w)+part*1048576+(row+j*16+rc())*1024+k+gr()*8,16);acc[j]=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(a,b,acc[j]);}}
 __attribute__((shared)) float raw[16*33];
 f8 sum{};
 if(part<2){
  for(uint j=0;j<2;j++)for(uint e=0;e<8;e++)raw[(gr()*8+e)*33+j*16+rc()]=acc[j][e];
  __builtin_amdgcn_s_barrier();
  for(uint k=0;k<32;k+=16){h8 x{},ones{};for(uint e=0;e<8;e++){float v=raw[rc()*33+k+gr()*8+e];x[e]=(_Float16)(v*v);ones[e]=(_Float16)1.f;}sum=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(x,ones,sum);}
 }
 for(uint j=0;j<2;j++)for(uint e=0;e<8;e++){float v=acc[j][e];if(part<2){float scale=part==0?5.65625f*w[1572864+row/32]:1.f;v*=__builtin_amdgcn_rsqf(maxf(sum[e],6.198883056640625e-5f))*scale;}out[(part*tokens+first+gr()*8+e)*1024+row+j*16+rc()]=byte_F(v);}
}
WAVE void vit_qkv_project_normalize_fused_f16compact(const float*in,const float*w,float*out,uint tokens){
 uint perpart=(tokens/16)*32,part=bid()/perpart,local=bid()%perpart,first=local/32*16,row=local%32*32;if(part>=3)return;f8 acc[2]{};
 for(uint k=0;k<1024;k+=16){h8 a{};for(uint e=0;e<8;e++)a[e]=(_Float16)in[(first+rc())*1024+k+gr()*8+e];for(uint j=0;j<2;j++){h8 b{};__builtin_memcpy(&b,reinterpret_cast<const _Float16*>(w)+part*1048576+(row+j*16+rc())*1024+k+gr()*8,16);acc[j]=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(a,b,acc[j]);}}
 __attribute__((shared)) float raw[16*33];
 f8 sum{};
 if(part<2){
  for(uint j=0;j<2;j++)for(uint e=0;e<8;e++)raw[(gr()*8+e)*33+j*16+rc()]=acc[j][e];
  __builtin_amdgcn_s_barrier();
  for(uint k=0;k<32;k+=16){h8 x{},ones{};for(uint e=0;e<8;e++){float v=raw[rc()*33+k+gr()*8+e];x[e]=(_Float16)(v*v);ones[e]=(_Float16)1.f;}sum=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(x,ones,sum);}
 }
 for(uint j=0;j<2;j++)for(uint e=0;e<8;e++){float v=acc[j][e];if(part<2){float scale=part==0?5.65625f*w[1572864+row/32]:1.f;v*=__builtin_amdgcn_rsqf(maxf(sum[e],6.198883056640625e-5f))*scale;}out[(part*tokens+first+gr()*8+e)*1024+row+j*16+rc()]=F(v);}
}
