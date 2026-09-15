// Production C32 FAST4 attention precision, separate from exact reference.
// All kernels flat grid ceil(work_items/256), block32; token count divisible64.
#ifndef HIP_C32_DIRECT_WEIGHT8
#define HIP_C32_DIRECT_WEIGHT8 1
#endif
#ifndef HIP_C32_WEIGHT_DWORD
#define HIP_C32_WEIGHT_DWORD 1
#endif
#ifndef HIP_C32_LOCAL_QKV_SYNC
#define HIP_C32_LOCAL_QKV_SYNC 1
#endif
#ifndef HIP_C32_REGISTER_FFN
#define HIP_C32_REGISTER_FFN 1
#endif
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

using i2=int __attribute__((ext_vector_type(2)));
using f8=float __attribute__((ext_vector_type(8)));
using h8=_Float16 __attribute__((ext_vector_type(8)));
#define WAVE KERNEL __attribute__((amdgpu_flat_work_group_size(32,32)))
DEV uint rc(){return __builtin_amdgcn_workitem_id_x()&15;}
DEV uint gr(){return (__builtin_amdgcn_workitem_id_x()&31)>>4;}
DEV uint bid(){return __builtin_amdgcn_workgroup_id_x();}
// D3D explicit f32tof16 maps to RTZ here; matrix Cast<F16> remains RNE.
#ifndef HIP_C32_RTZ_ISA
#define HIP_C32_RTZ_ISA 1
#endif
#if HIP_C32_RTZ_ISA
DEV float Hrtz(float x){uint h;float result;
 asm("v_cvt_pkrtz_f16_f32 %0, %1, %1" : "=v"(h) : "v"(x));
 asm("v_cvt_f32_f16 %0, %1" : "=v"(result) : "v"(h));
 return result;
}
#else
DEV float Hrtz(float x){uint b=bits(x),a=b&0x7fffffffu,sg=(b>>16)&0x8000u;int e=int(a>>23)-127;
 if(a>=0x7f800000u)return from_half(sg|0x7c00u|((a&0x7fffffu)?0x200u:0u));
 if(e>15)return from_half(sg|0x7bffu);
 if(e<-24)return from_half(sg);
 if(e<-14)return from_half(sg|(((a&0x7fffffu)|0x800000u)>>uint(-e-1)));
 return from_half(sg|((a>>13)-0x1c000u));
}
#endif
DEV uint fp8(float f){return uint(__builtin_amdgcn_cvt_pk_fp8_f32(clampf(f,-448.f,448.f),0.f,0,false))&255u;}
DEV void put(i2&v,uint e,float x){v[e/4]=int(uint(v[e/4])|(fp8(x)<<(8*(e%4))));}

DEV void sync_window(){__builtin_amdgcn_fence(3,"workgroup");__builtin_amdgcn_s_barrier();__builtin_amdgcn_fence(2,"workgroup");}

// Only for wave-private LDS rows: order memory without waiting for other waves.
DEV void sync_owned_rows(){
#if HIP_C32_LOCAL_QKV_SYNC
 __builtin_amdgcn_fence(3,"workgroup");__builtin_amdgcn_fence(2,"workgroup");
#else
 sync_window();
#endif
}

DEV float scale_piece(float v){float m=absf(v);if(m<.015625f){float x=m*512.f;uint q=uint(x);float r=x-float(q);q+=uint(r>.5f||(r==.5f&&(q&1u)));if(q>7)q=7;return value((bits(v)&0x80000000u)|bits(float(q)/512.f));}return F(v);}
// Packed attention: shared raw/exp scratch 8448 bytes + normalized/prob/AV bytes 6912.
using ushort=unsigned short;
DEV void put_bits(i2&v,uint e,uint b){v[e/4]=int(uint(v[e/4])|((b&255u)<<(8*(e%4))));}
DEV uint matrix_byte(const float*w,uint start,uint index){
#ifdef HIP_PREPACKED_WEIGHTS
 return reinterpret_cast<const unsigned char*>(w+start)[index];
#else
 return fp8(w[start+index]);
#endif
}
DEV i2 matrix8(const float*w,uint index){
#if HIP_C32_DIRECT_WEIGHT8 && defined(HIP_PREPACKED_WEIGHTS)
 i2 result;__builtin_memcpy(&result,reinterpret_cast<const unsigned char*>(w)+index,8);return result;
#else
 i2 result{};for(uint e=0;e<8;e++)put_bits(result,e,matrix_byte(w,0,index+e));return result;
#endif
}
// Byte-preserving packed LDS reads; memcpy does not impose pointer alignment.
DEV i2 load8(const unsigned char*p){
#ifdef HIP_C32_LDS_VECTOR
 i2 result;__builtin_memcpy(&result,p,8);return result;
#else
 i2 result{};for(uint e=0;e<8;e++)put_bits(result,e,p[e]);return result;
#endif
}
DEV float mapped_c32_input(const float*in,uint window,uint token,uint channel,uint width,uint height,uint sx,uint sy){uint ww=width+2*sx;int x=int((window%(ww/8))*8+token%8)-int(sx),y=int((window/(ww/8))*8+token/8)-int(sy);return x>=0&&y>=0&&x<int(width)&&y<int(height)?in[(uint(y)*width+uint(x))*32+channel]:0.f;}
template<bool HalfOutput,bool Mapped=false>
DEV void c32_fused_body(const float*raw_input,const float*fw,const float*w,float*out,uint windows,uint residual_mode,uint raw_output,uint sourcew=0,uint sourceh=0,uint sx=0,uint sy=0){
 uint window=bid();if(window>=windows)return;uint tid=__builtin_amdgcn_workitem_id_x(),wave=tid/32,first=wave*16,base=window*64;
 union Scratch {float raw[64*33];_Float16 ex[64*66];unsigned char hidden[64*132];};
 __attribute__((shared)) Scratch scratch;
 __attribute__((shared)) unsigned char packed[3*64*36];
#if HIP_C32_REGISTER_FFN
 h8 saved_ffn[2];
 __attribute__((shared)) unsigned char ffn8[64*36];
#else
 __attribute__((shared)) _Float16 ffn[64*34];
#endif
 if(residual_mode!=0&&residual_mode!=3)return;
 // Input64x36 and expand weights128x36 fill the norm scratch temporarily.
 for(uint i=tid;i<64*36;i+=128){uint row=i/36,k=i%36;packed[i]=k<32?static_cast<unsigned char>(fp8(Mapped?mapped_c32_input(raw_input,window,row,k,sourcew,sourceh,sx,sy):raw_input[(base+row)*32+k])):0;}
#if HIP_C32_WEIGHT_DWORD && defined(HIP_PREPACKED_WEIGHTS)
 for(uint i=tid;i<128*9;i+=128){uint row=i/9,k=(i%9)*4;uint word=0;if(k<32)__builtin_memcpy(&word,reinterpret_cast<const unsigned char*>(fw+512)+row*32+k,4);__builtin_memcpy(packed+64*36+i*4,&word,4);}
#else
 for(uint i=tid;i<128*36;i+=128){uint row=i/36,k=i%36;packed[64*36+i]=k<32?static_cast<unsigned char>(matrix_byte(fw,512,row*32+k)):0;}
#endif
 sync_window();
 for(uint col=0;col<128;col+=16){f8 sum{};
  for(uint kt=0;kt<2;kt++){i2 a{},b{};uint k=kt*16+gr()*8;a=load8(packed+(first+rc())*36+k);b=load8(packed+64*36+(col+rc())*36+k);sum=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,sum);}
  for(uint e=0;e<8;e++){float v=sum[e],g=clampf(v,-4.f,4.f),q=absf(g)*(-.055908203125f)+.447265625f,p=g*q+.89453125f;scratch.hidden[(first+gr()*8+e)*132+col+rc()]=static_cast<unsigned char>(fp8(v*p));}
 }
 sync_window();
 // Expand weights are dead; contract32x132 occupies 4224 of their former4608 bytes.
#if HIP_C32_WEIGHT_DWORD && defined(HIP_PREPACKED_WEIGHTS)
 for(uint i=tid;i<32*33;i+=128){uint row=i/33,k=(i%33)*4;uint word=0;if(k<128)__builtin_memcpy(&word,reinterpret_cast<const unsigned char*>(fw+4608)+row*128+k,4);__builtin_memcpy(packed+64*36+i*4,&word,4);}
#else
 for(uint i=tid;i<32*132;i+=128){uint row=i/132,k=i%132;packed[64*36+i]=k<128?static_cast<unsigned char>(matrix_byte(fw,4608,row*128+k)):0;}
#endif
 sync_window();f8 acc[2];acc[0]=f8{};acc[1]=f8{};
 if(residual_mode==0){for(uint ci=0;ci<2;ci++)for(uint e=0;e<8;e++){uint row=first+gr()*8+e,c=ci*16+rc();acc[ci][e]=clampf(Mapped?mapped_c32_input(raw_input,window,row,c,sourcew,sourceh,sx,sy):raw_input[(base+row)*32+c],-448.f,448.f)*fw[8704+c];}}
 else{for(uint part=0;part<3;part++)for(uint ci=0;ci<2;ci++){uint c=ci*16+rc();float remaining=fw[8704+c],piece=0;for(uint j=0;j<=part;j++){piece=scale_piece(remaining);remaining-=piece;}
   for(uint kt=0;kt<2;kt++){i2 a{},b{};for(uint e=0;e<8;e++){uint k=kt*16+gr()*8+e;put_bits(a,e,packed[(first+rc())*36+k]);put_bits(b,e,k==c?fp8(piece):0u);}acc[ci]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,acc[ci]);}
  }}
 for(uint chunk=0;chunk<4;chunk++)for(uint ci=0;ci<2;ci++){
  for(uint kt=0;kt<2;kt++){i2 a{},b{};uint k=chunk*32+kt*16+gr()*8;a=load8(scratch.hidden+(first+rc())*132+k);b=load8(packed+64*36+(ci*16+rc())*132+k);acc[ci]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,acc[ci]);}
 }
 for(uint ci=0;ci<2;ci++)for(uint e=0;e<8;e++){
#if HIP_C32_REGISTER_FFN
  float v=Hrtz(acc[ci][e]);saved_ffn[ci][e]=(_Float16)v;ffn8[(first+gr()*8+e)*36+ci*16+rc()]=static_cast<unsigned char>(fp8(v));
#else
  ffn[(first+gr()*8+e)*34+ci*16+rc()]=(_Float16)Hrtz(acc[ci][e]);
#endif
 }
 sync_window();
 // A single raw QKV plane is reused after its norm has been packed separately.
 for(uint part=0;part<3;part++){
  for(uint col=0;col<32;col+=16){f8 acc{};
   for(uint kt=0;kt<2;kt++){i2 a{},b{};
#if HIP_C32_REGISTER_FFN
    a=load8(ffn8+(first+rc())*36+kt*16+gr()*8);
#endif
    for(uint e=0;e<8;e++){uint k=kt*16+gr()*8+e;
#if !HIP_C32_REGISTER_FFN
     put(a,e,float(ffn[(first+rc())*34+k]));
#endif
    }b=matrix8(w,part*1024+(col+rc())*32+kt*16+gr()*8);acc=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,acc);}
   for(uint e=0;e<8;e++)scratch.raw[(first+gr()*8+e)*33+col+rc()]=acc[e];
  }
  sync_owned_rows();f8 sum{};
  if(part<2)for(uint kt=0;kt<2;kt++){h8 a{},ones{};for(uint e=0;e<8;e++){uint k=kt*16+gr()*8+e;float v=scratch.raw[(first+rc())*33+k];a[e]=(_Float16)(v*v);ones[e]=(_Float16)1.f;}sum=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(a,ones,sum);}
  for(uint col=0;col<32;col+=16)for(uint e=0;e<8;e++){uint row=first+gr()*8+e;float v=scratch.raw[row*33+col+rc()];if(part<2)v*=__builtin_amdgcn_rsqf(maxf(sum[e],6.198883056640625e-5f))*(part==0?w[8192]:1.f);packed[(part*64+row)*36+col+rc()]=static_cast<unsigned char>(fp8(v));}
  sync_owned_rows();
 }
#if HIP_C32_LOCAL_QKV_SYNC
 sync_window(); // Attention reads K/V rows owned by all four waves.
#endif
 // Q/K packed rows: 36-byte stride. Exponent values stored exactly as half bits.
 for(uint key=0;key<64;key+=16){f8 acc{};
  for(uint kt=0;kt<2;kt++){i2 a{},b{};uint k=kt*16+gr()*8;a=load8(packed+(first+rc())*36+k);b=load8(packed+(64+key+rc())*36+k);acc=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,acc);}
  for(uint e=0;e<8;e++){uint q=first+gr()*8+e,k=key+rc();float score=acc[e]+w[4096+q*64+k],affine=clampf(score*.044921875f+1.30078125f,1.03125f,1.5693359375f);uint ah=(bits(affine)>>13)-0x1c000u;ushort hb=static_cast<ushort>(((ah<<5)+0x8000u)&65535u);scratch.ex[q*66+k]=__builtin_bit_cast(_Float16,hb);}
 }
 sync_window();
 // Scores no longer consume Q/K; their 4608 bytes become 64 probability rows of 68 bytes.
 {f8 sum{};for(uint kt=0;kt<4;kt++){h8 a{},ones{};for(uint e=0;e<8;e++){uint k=kt*16+gr()*8+e;a[e]=scratch.ex[(first+rc())*66+k];ones[e]=(_Float16)1.f;}sum=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(a,ones,sum);}
  for(uint key=0;key<64;key+=16)for(uint e=0;e<8;e++){uint row=first+gr()*8+e,k=key+rc();float v=float(scratch.ex[row*66+k])*(1.f/sum[e]);packed[row*68+k]=static_cast<unsigned char>(fp8(v));}
 }
 sync_window();
 // Both AV column fragments stay live until every wave has finished reading probability rows.
 f8 av[2];
 for(uint ci=0;ci<2;ci++){f8 acc{};uint col=ci*16;
  for(uint kt=0;kt<4;kt++){i2 a{},b{};for(uint e=0;e<8;e++){uint k=kt*16+gr()*8+e;put_bits(a,e,packed[(first+rc())*68+k]);put_bits(b,e,packed[(128+k)*36+col+rc()]);}acc=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,acc);}av[ci]=acc;
 }
 sync_window();
 for(uint ci=0;ci<2;ci++)for(uint e=0;e<8;e++)packed[(first+gr()*8+e)*36+ci*16+rc()]=static_cast<unsigned char>(fp8(av[ci][e]));
 sync_window();
 for(uint col=0;col<32;col+=16){f8 acc{};
  for(uint kt=0;kt<2;kt++){i2 a{},b{};for(uint e=0;e<8;e++){uint k=kt*16+gr()*8+e;put_bits(a,e,packed[(first+rc())*36+k]);}b=matrix8(w,3072+(col+rc())*32+kt*16+gr()*8);acc=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,acc);}
  for(uint e=0;e<8;e++){uint i=(base+first+gr()*8+e)*32+col+rc();float residual;
#if HIP_C32_REGISTER_FFN
   residual=float(saved_ffn[col/16][e]);
#else
   residual=float(ffn[(first+gr()*8+e)*34+col+rc()]);
#endif
   float prod=residual*w[8193+col+rc()],v=Hrtz(acc[e]+prod);if constexpr(HalfOutput)reinterpret_cast<_Float16*>(out)[i]=(_Float16)(raw_output?v:F(v));else out[i]=raw_output?v:F(v);}
 }
}

KERNEL __attribute__((amdgpu_flat_work_group_size(128,128)))
void c32_fast_ffn_attention_fused(const float*in,const float*fw,const float*w,float*out,uint windows,uint mode,uint raw){c32_fused_body<false>(in,fw,w,out,windows,mode,raw);}
KERNEL __attribute__((amdgpu_flat_work_group_size(128,128)))
void c32_fast_ffn_attention_fused_half(const float*in,const float*fw,const float*w,float*out,uint windows,uint mode,uint raw){c32_fused_body<true>(in,fw,w,out,windows,mode,raw);}

KERNEL __attribute__((amdgpu_flat_work_group_size(128,128)))
void c32_fast_ffn_attention_fused_half_mapped(const float*in,const float*fw,const float*w,float*out,uint windows,uint mode,uint raw,uint width,uint height,uint sx,uint sy){c32_fused_body<true,true>(in,fw,w,out,windows,mode,raw,width,height,sx,sy);}
