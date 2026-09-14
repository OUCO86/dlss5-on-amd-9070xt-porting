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
DEV float F(float x){uint b=bits(x),a=b&0x7fffffffu,s=b&0x80000000u;if(a==0)return 0.f;
 if(a>=0x43e00000u)return value(s|0x43e00000u); // finite E4M3 saturation, including overflow
 if(a<0x3c800000u){float scaled=absf(x)*512.f;uint q=uint(scaled);float r=scaled-float(q);q+=uint(r>.5f||(r==.5f&&(q&1u)));float f=float(q)/512.f;return s?-f:f;}
 uint r=(a+0x7ffffu+((a>>20)&1u))&0xfff00000u;return value(s|(r>0x43e00000u?0x43e00000u:r));}

using f8=float __attribute__((ext_vector_type(8)));
using h8=_Float16 __attribute__((ext_vector_type(8)));
using i2=int __attribute__((ext_vector_type(2)));
#define WAVE KERNEL __attribute__((amdgpu_flat_work_group_size(32,32)))
DEV uint rc(){return __builtin_amdgcn_workitem_id_x()&15u;}
DEV uint gr(){return __builtin_amdgcn_workitem_id_x()>>4;}
DEV uint bid(){return __builtin_amdgcn_workgroup_id_x();}
DEV void pack(i2&x,uint e,float v){uint b=uint(__builtin_amdgcn_cvt_pk_fp8_f32(clampf(v,-448.f,448.f),0.f,0,false))&255;x[e/4]=int(uint(x[e/4])|(b<<(8*(e%4))));}
DEV f8 dot8(const float*in,const float*w,uint first,uint row,uint channels,uint begin,uint end,f8 a){for(uint k=begin;k<end;k+=16){i2 x{},y{};for(uint e=0;e<8;e++){uint j=k+gr()*8+e;pack(x,e,in[(first+rc())*channels+j]);pack(y,e,w[(row+rc())*channels+j]);}a=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(x,y,a);}return a;}
WAVE void vit_expand(const float*in,const float*w,float*out,uint tokens,uint inputs,uint outputs){uint first=bid()/(outputs/16)*16,row=bid()%(outputs/16)*16;if(first>=tokens)return;f8 a{};a=dot8(in,w,first,row,inputs,0,inputs,a);for(uint e=0;e<8;e++){float v=a[e],g=clampf(v,-4.f,4.f),poly=__builtin_fmaf(g,absf(g)*(-.055908203125f)+.447265625f,.89453125f);out[(first+gr()*8+e)*outputs+row+rc()]=F(v*poly);}}
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
DEV float Hrtz(float x){uint b=bits(x),a=b&0x7fffffffu,s=(b>>16)&0x8000u;int e=int(a>>23)-127;if(a>=0x7f800000u)return from_half(s|0x7c00u|((a&0x7fffffu)?0x200u:0u));if(e>15)return from_half(s|0x7bffu);if(e<-24)return from_half(s);if(e<-14)return from_half(s|(((a&0x7fffffu)|0x800000u)>>uint(-e-1)));return from_half(s|((a>>13)-0x1c000u));}
// scores work=T*T*32; T%16=0; ex[query][head32][key].
WAVE void vit_attention_scores_fast(const float*in,float*out,uint tokens){uint kt= tokens/16,key=(bid()%kt)*16,head=(bid()/kt)%32,first=bid()/(kt*32)*16;if(first>=tokens)return;f8 a{};for(uint k=0;k<32;k+=16){i2 x{},y{};for(uint e=0;e<8;e++){uint j=k+gr()*8+e;pack(x,e,in[(first+rc())*1024+head*32+j]);pack(y,e,in[(tokens+key+rc())*1024+head*32+j]);}a=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(x,y,a);}for(uint e=0;e<8;e++){float af=clampf(a[e]*from_half(0x2dbb)+1.708984375f,1.439453125f,1.9775390625f);uint hb=(bits(af)>>13)-0x1c000u;out[((first+gr()*8+e)*32+head)*tokens+key+rc()]=from_half(((hb<<4)+0x4000u)&65535u);}}
// inverse SPECIAL work=T*32*16, not T*32. One wave handles16 queries for one head.
WAVE void vit_attention_inverse_fast(const float*ex,float*out,uint tokens){uint head=bid()%32,first=bid()/32*16;if(first>=tokens)return;f8 a{};for(uint k=0;k<tokens;k+=16){h8 x{},ones{};for(uint e=0;e<8;e++){uint key=k+gr()*8+e;x[e]=(_Float16)ex[((first+rc())*32+head)*tokens+key];ones[e]=(_Float16)1.f;}a=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(x,ones,a);}if(rc()==0)for(uint e=0;e<8;e++)out[(first+gr()*8+e)*32+head]=1.f/a[e];}
WAVE void vit_attention_av_fast(const float*in,const float*ex,const float*inv,float*out,uint tokens){uint first=bid()/64*16,head=(bid()%64)/2,col=(bid()%2)*16;if(first>=tokens)return;f8 a{};for(uint k=0;k<tokens;k+=16){i2 x{},y{};for(uint e=0;e<8;e++){uint key=k+gr()*8+e;pack(x,e,ex[((first+rc())*32+head)*tokens+key]);pack(y,e,in[(2*tokens+key)*1024+head*32+col+rc()]);}a=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(x,y,a);}for(uint e=0;e<8;e++){uint q=first+gr()*8+e;out[q*1024+head*32+col+rc()]=F(Hrtz(a[e]*inv[q*32+head]));}}
// Production decoder build leaves NATIVE_DECODER_HW_H=0: H is integer RNE.
WAVE void decoder_project2x(const float*in,const float*w,const float*skip,float*out,uint iw,uint ih,uint ow,uint oh,uint inputs,uint outputs){uint first=bid()/(outputs/16)*16,row=bid()%(outputs/16)*16;if(first>=iw*ih)return;uint parts=inputs==1024?4:1;f8 total{};for(uint p=0;p<parts;p++){f8 a{};for(uint k=p*(inputs/parts);k<(p+1)*(inputs/parts);k+=16){h8 x{},y{};for(uint e=0;e<8;e++){uint j=k+gr()*8+e;x[e]=(_Float16)in[(first+rc())*inputs+j];y[e]=(_Float16)w[(row+rc())*inputs+j];}a=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(x,y,a);}for(uint e=0;e<8;e++)total[e]=p?total[e]+a[e]:a[e];}for(uint e=0;e<8;e++){uint token=first+gr()*8+e;float t=H(total[e]);for(uint dy=0;dy<2;dy++)for(uint dx=0;dx<2;dx++){uint x=(token%iw)*2+dx,y=(token/iw)*2+dy;if(x>=ow||y>=oh)continue;uint i=(y*ow+x)*outputs+row+rc();float merged=H(t+F(skip[i])*w[inputs*outputs+row+rc()]);out[i]=outputs==32?merged:F(merged);}}}
DEV f8 dot16(const float*in,const float*w,uint first,uint row,uint instride,uint kcols,uint inoff,uint woff,f8 a){for(uint k=0;k<kcols;k+=16){h8 x{},y{};for(uint e=0;e<8;e++){uint j=k+gr()*8+e;x[e]=(_Float16)in[(first+rc())*instride+inoff+j];y[e]=(_Float16)w[woff+(row+rc())*kcols+j];}a=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(x,y,a);}return a;}
WAVE void split_mix(const float*in,const float*w,float*out,uint tokens){uint first=bid()/32*16,row=bid()%32*16;if(first>=tokens)return;f8 a{};a=dot16(in,w,first,row,512,512,0,0,a);for(uint e=0;e<8;e++)out[(first+gr()*8+e)*512+row+rc()]=F(Hrtz(a[e]));}
WAVE void split_expand(const float*in,const float*w,float*out,uint tokens){uint first=bid()/128*16,col=bid()%128*16,g=col/256,row=col%256;if(first>=tokens)return;f8 a{};a=dot16(in,w,first,row,512,64,g*64,262144+g*16384,a);for(uint e=0;e<8;e++){float v=Hrtz(a[e]),gate=clampf(v,-4.f,4.f),poly=gate*(absf(gate)*(-.055908203125f)+.447265625f)+.89453125f;out[(first+gr()*8+e)*2048+col+rc()]=F(v*poly);}}
WAVE void split_contract(const float*in,const float*w,float*out,uint tokens){uint first=bid()/32*16,col=bid()%32*16,g=col/64,row=col%64;if(first>=tokens)return;f8 a{};a=dot16(in,w,first,row,2048,256,g*256,393216+g*16384,a);for(uint e=0;e<8;e++)out[(first+gr()*8+e)*512+col+rc()]=F(Hrtz(a[e]));}
// stream0 FFWD projection build omits NATIVE_HW_H: initial and final H are integer RNE.
WAVE void split_projection(const float*in,const float*w,const float*skip,float*out,uint tokens){uint first=bid()/32*16,row=bid()%32*16;if(first>=tokens)return;f8 a{};for(uint e=0;e<8;e++)a[e]=H(skip[(first+gr()*8+e)*512+row+rc()]*w[262144+row+rc()]);a=dot8(in,w,first,row,512,0,512,a);for(uint e=0;e<8;e++)out[(first+gr()*8+e)*512+row+rc()]=F(H(a[e]));}
