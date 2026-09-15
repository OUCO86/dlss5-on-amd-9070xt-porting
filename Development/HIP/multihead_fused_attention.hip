#ifndef HIP_MH_INPUT_DWORD
#define HIP_MH_INPUT_DWORD 1
#endif
// Production MH score/probability/AV fused; normalized f32 HWC input.
// All kernels flat grid ceil(work_items/256), block32; token count divisible64.
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
DEV float Hrtz(float x){uint b=bits(x),a=b&0x7fffffffu,sg=(b>>16)&0x8000u;int e=int(a>>23)-127;
 if(a>=0x7f800000u)return from_half(sg|0x7c00u|((a&0x7fffffu)?0x200u:0u));
 if(e>15)return from_half(sg|0x7bffu);
 if(e<-24)return from_half(sg);
 if(e<-14)return from_half(sg|(((a&0x7fffffu)|0x800000u)>>uint(-e-1)));
 return from_half(sg|((a>>13)-0x1c000u));
}
DEV uint fp8(float f){return uint(__builtin_amdgcn_cvt_pk_fp8_f32(clampf(f,-448.f,448.f),0.f,0,false))&255u;}
DEV void put(i2&v,uint e,float x){v[e/4]=int(uint(v[e/4])|(fp8(x)<<(8*(e%4))));}

DEV void sync_window(){__builtin_amdgcn_fence(3,"workgroup");__builtin_amdgcn_s_barrier();__builtin_amdgcn_fence(2,"workgroup");}

// Packed attention: shared raw/exp scratch 8448 bytes + normalized/prob/AV bytes 6912.
using ushort=unsigned short;
DEV void put_bits(i2&v,uint e,uint b){v[e/4]=int(uint(v[e/4])|((b&255u)<<(8*(e%4))));}
DEV uint raster(uint win,uint tok,uint width){return ((win/(width/8))*8+tok/8)*width+(win%(width/8))*8+tok%8;}
// Grid=(width/8)*(height/8)*(channels/32), block128. No QKV/norm/projection here.
KERNEL __attribute__((amdgpu_flat_work_group_size(128,128)))
void mh_attention_fused(const float*normalized,const float*w,float*out,uint width,uint height,uint channels){
 uint heads=channels/32,windows=(width/8)*(height/8),wh=bid();
 if((channels!=64&&channels!=128&&channels!=256&&channels!=512)||width%8||height%8||wh>=windows*heads)return;
 uint win=wh/heads,head=wh%heads,tid=__builtin_amdgcn_workitem_id_x(),wave=tid/32,first=wave*16;
 __attribute__((shared)) _Float16 ex[64*66];
 __attribute__((shared)) unsigned char packed[3*64*36];
 // 6912-byte packed Q/K/V. No global intermediate writes.
 for(uint i=tid;i<3*64*32;i+=128){uint part=i/(64*32),tok=(i/32)%64,c=i%32,p=raster(win,tok,width);packed[(part*64+tok)*36+c]=static_cast<unsigned char>(fp8(normalized[(p*3+part)*channels+head*32+c]));}
 sync_window();
 for(uint key=0;key<64;key+=16){f8 acc{};
  for(uint kt=0;kt<2;kt++){i2 a{},b{};for(uint e=0;e<8;e++){uint k=kt*16+gr()*8+e;put_bits(a,e,packed[(first+rc())*36+k]);put_bits(b,e,packed[(64+key+rc())*36+k]);}acc=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,acc);}
  for(uint e=0;e<8;e++){uint q=first+gr()*8+e,k=key+rc();float score=acc[e]+w[4*channels*channels+head*4096+q*64+k],affine=clampf(score*.044921875f+1.30078125f,1.03125f,1.5693359375f);uint ah=(bits(affine)>>13)-0x1c000u;ushort hb=static_cast<ushort>(((ah<<5)+0x8000u)&65535u);ex[q*66+k]=__builtin_bit_cast(_Float16,hb);}
 }
 sync_window();
 // MH production partial0 sums keys0..15,32..47; partial1 sums16..31,48..63.
 // Keep this distinct from C32 FAST4's sequential64-key accumulator.
 f8 sums[2];for(uint side=0;side<2;side++){f8 sum{};for(uint half=0;half<2;half++){h8 a{},ones{};for(uint e=0;e<8;e++){uint k=side*16+half*32+gr()*8+e;a[e]=ex[(first+rc())*66+k];ones[e]=(_Float16)1.f;}sum=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(a,ones,sum);}sums[side]=sum;}
 // Q/K are dead; probability64x68 occupies4352 of their4608 bytes. V starts4608.
 for(uint key=0;key<64;key+=16)for(uint e=0;e<8;e++){uint row=first+gr()*8+e,k=key+rc();float inv=1.f/(sums[0][e]+sums[1][e]);packed[row*68+k]=static_cast<unsigned char>(fp8(float(ex[row*66+k])*inv));}
 sync_window();
 for(uint col=0;col<32;col+=16){f8 acc{};for(uint kt=0;kt<4;kt++){i2 a{},b{};for(uint e=0;e<8;e++){uint k=kt*16+gr()*8+e;put_bits(a,e,packed[(first+rc())*68+k]);put_bits(b,e,packed[(128+k)*36+col+rc()]);}acc=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,acc);}for(uint e=0;e<8;e++){uint p=raster(win,first+gr()*8+e,width);out[p*channels+head*32+col+rc()]=F(acc[e]);}}
}

// Byte-input ABI paired with mh_qkv_normalize_fast_wave_fp8.
KERNEL __attribute__((amdgpu_flat_work_group_size(128,128)))
void mh_attention_fused_fp8(const unsigned char*normalized,const float*w,float*out,uint width,uint height,uint channels){
 uint heads=channels/32,windows=(width/8)*(height/8),wh=bid();
 if((channels!=64&&channels!=128&&channels!=256&&channels!=512)||width%8||height%8||wh>=windows*heads)return;
 uint win=wh/heads,head=wh%heads,tid=__builtin_amdgcn_workitem_id_x(),wave=tid/32,first=wave*16;
 __attribute__((shared)) _Float16 ex[64*66];
 __attribute__((shared)) unsigned char packed[3*64*36];
 // 6912-byte packed Q/K/V. No global intermediate writes.
#if HIP_MH_INPUT_DWORD
 for(uint i=tid;i<3*64*8;i+=128){uint part=i/(64*8),tok=(i/8)%64,c=(i%8)*4,p=raster(win,tok,width),word;__builtin_memcpy(&word,normalized+(p*3+part)*channels+head*32+c,4);__builtin_memcpy(packed+(part*64+tok)*36+c,&word,4);}
#else
 for(uint i=tid;i<3*64*32;i+=128){uint part=i/(64*32),tok=(i/32)%64,c=i%32,p=raster(win,tok,width);packed[(part*64+tok)*36+c]=normalized[(p*3+part)*channels+head*32+c];}
#endif
 sync_window();
 for(uint key=0;key<64;key+=16){f8 acc{};
  for(uint kt=0;kt<2;kt++){i2 a{},b{};for(uint e=0;e<8;e++){uint k=kt*16+gr()*8+e;put_bits(a,e,packed[(first+rc())*36+k]);put_bits(b,e,packed[(64+key+rc())*36+k]);}acc=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,acc);}
  for(uint e=0;e<8;e++){uint q=first+gr()*8+e,k=key+rc();float score=acc[e]+w[4*channels*channels+head*4096+q*64+k],affine=clampf(score*.044921875f+1.30078125f,1.03125f,1.5693359375f);uint ah=(bits(affine)>>13)-0x1c000u;ushort hb=static_cast<ushort>(((ah<<5)+0x8000u)&65535u);ex[q*66+k]=__builtin_bit_cast(_Float16,hb);}
 }
 sync_window();
 // MH production partial0 sums keys0..15,32..47; partial1 sums16..31,48..63.
 // Keep this distinct from C32 FAST4's sequential64-key accumulator.
 f8 sums[2];for(uint side=0;side<2;side++){f8 sum{};for(uint half=0;half<2;half++){h8 a{},ones{};for(uint e=0;e<8;e++){uint k=side*16+half*32+gr()*8+e;a[e]=ex[(first+rc())*66+k];ones[e]=(_Float16)1.f;}sum=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(a,ones,sum);}sums[side]=sum;}
 // Q/K are dead; probability64x68 occupies4352 of their4608 bytes. V starts4608.
 for(uint key=0;key<64;key+=16)for(uint e=0;e<8;e++){uint row=first+gr()*8+e,k=key+rc();float inv=1.f/(sums[0][e]+sums[1][e]);packed[row*68+k]=static_cast<unsigned char>(fp8(float(ex[row*66+k])*inv));}
 sync_window();
 for(uint col=0;col<32;col+=16){f8 acc{};for(uint kt=0;kt<4;kt++){i2 a{},b{};for(uint e=0;e<8;e++){uint k=kt*16+gr()*8+e;put_bits(a,e,packed[(first+rc())*68+k]);put_bits(b,e,packed[(128+k)*36+col+rc()]);}acc=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,acc);}for(uint e=0;e<8;e++){uint p=raster(win,first+gr()*8+e,width);out[p*channels+head*32+col+rc()]=F(acc[e]);}}
}

// Byte output paired with byte-input projection.
KERNEL __attribute__((amdgpu_flat_work_group_size(128,128)))
void mh_attention_fused_fp8_out(const unsigned char*normalized,const float*w,unsigned char*out,uint width,uint height,uint channels){
 uint heads=channels/32,windows=(width/8)*(height/8),wh=bid();
 if((channels!=64&&channels!=128&&channels!=256&&channels!=512)||width%8||height%8||wh>=windows*heads)return;
 uint win=wh/heads,head=wh%heads,tid=__builtin_amdgcn_workitem_id_x(),wave=tid/32,first=wave*16;
 __attribute__((shared)) _Float16 ex[64*66];
 __attribute__((shared)) unsigned char packed[3*64*36];
 // 6912-byte packed Q/K/V. No global intermediate writes.
#if HIP_MH_INPUT_DWORD
 for(uint i=tid;i<3*64*8;i+=128){uint part=i/(64*8),tok=(i/8)%64,c=(i%8)*4,p=raster(win,tok,width),word;__builtin_memcpy(&word,normalized+(p*3+part)*channels+head*32+c,4);__builtin_memcpy(packed+(part*64+tok)*36+c,&word,4);}
#else
 for(uint i=tid;i<3*64*32;i+=128){uint part=i/(64*32),tok=(i/32)%64,c=i%32,p=raster(win,tok,width);packed[(part*64+tok)*36+c]=normalized[(p*3+part)*channels+head*32+c];}
#endif
 sync_window();
 for(uint key=0;key<64;key+=16){f8 acc{};
  for(uint kt=0;kt<2;kt++){i2 a{},b{};for(uint e=0;e<8;e++){uint k=kt*16+gr()*8+e;put_bits(a,e,packed[(first+rc())*36+k]);put_bits(b,e,packed[(64+key+rc())*36+k]);}acc=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,acc);}
  for(uint e=0;e<8;e++){uint q=first+gr()*8+e,k=key+rc();float score=acc[e]+w[4*channels*channels+head*4096+q*64+k],affine=clampf(score*.044921875f+1.30078125f,1.03125f,1.5693359375f);uint ah=(bits(affine)>>13)-0x1c000u;ushort hb=static_cast<ushort>(((ah<<5)+0x8000u)&65535u);ex[q*66+k]=__builtin_bit_cast(_Float16,hb);}
 }
 sync_window();
 // MH production partial0 sums keys0..15,32..47; partial1 sums16..31,48..63.
 // Keep this distinct from C32 FAST4's sequential64-key accumulator.
 f8 sums[2];for(uint side=0;side<2;side++){f8 sum{};for(uint half=0;half<2;half++){h8 a{},ones{};for(uint e=0;e<8;e++){uint k=side*16+half*32+gr()*8+e;a[e]=ex[(first+rc())*66+k];ones[e]=(_Float16)1.f;}sum=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(a,ones,sum);}sums[side]=sum;}
 // Q/K are dead; probability64x68 occupies4352 of their4608 bytes. V starts4608.
 for(uint key=0;key<64;key+=16)for(uint e=0;e<8;e++){uint row=first+gr()*8+e,k=key+rc();float inv=1.f/(sums[0][e]+sums[1][e]);packed[row*68+k]=static_cast<unsigned char>(fp8(float(ex[row*66+k])*inv));}
 sync_window();
 for(uint col=0;col<32;col+=16){f8 acc{};for(uint kt=0;kt<4;kt++){i2 a{},b{};for(uint e=0;e<8;e++){uint k=kt*16+gr()*8+e;put_bits(a,e,packed[(first+rc())*68+k]);put_bits(b,e,packed[(128+k)*36+col+rc()]);}acc=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,acc);}for(uint e=0;e<8;e++){uint p=raster(win,first+gr()*8+e,width);out[p*channels+head*32+col+rc()]=static_cast<unsigned char>(fp8(F(acc[e])));}}
}

KERNEL __attribute__((amdgpu_flat_work_group_size(256,256)))
void c64_attention_project(const unsigned char*normalized,const float*w,const float*feature,float*out,uint width,uint height,uint post,uint cropw,uint croph,uint sx,uint sy){
 const uint channels=64;
 uint windows=(width/8)*(height/8),win=bid();if(width%8||height%8||win>=windows)return;
 uint alltid=__builtin_amdgcn_workitem_id_x(),head=alltid/128,tid=alltid%128,wave=tid/32,first=wave*16;
 __attribute__((shared)) _Float16 all_ex[2*64*66];
 __attribute__((shared)) unsigned char all_packed[2*3*64*36];
 _Float16*ex=all_ex+head*64*66;unsigned char*packed=all_packed+head*3*64*36;
 unsigned char*avbytes=reinterpret_cast<unsigned char*>(all_ex);
 // 6912-byte packed Q/K/V. No global intermediate writes.
#if HIP_MH_INPUT_DWORD
 for(uint i=tid;i<3*64*8;i+=128){uint part=i/(64*8),tok=(i/8)%64,c=(i%8)*4,p=raster(win,tok,width),word;__builtin_memcpy(&word,normalized+(p*3+part)*channels+head*32+c,4);__builtin_memcpy(packed+(part*64+tok)*36+c,&word,4);}
#else
 for(uint i=tid;i<3*64*32;i+=128){uint part=i/(64*32),tok=(i/32)%64,c=i%32,p=raster(win,tok,width);packed[(part*64+tok)*36+c]=normalized[(p*3+part)*channels+head*32+c];}
#endif
 sync_window();
 for(uint key=0;key<64;key+=16){f8 acc{};
  for(uint kt=0;kt<2;kt++){i2 a{},b{};for(uint e=0;e<8;e++){uint k=kt*16+gr()*8+e;put_bits(a,e,packed[(first+rc())*36+k]);put_bits(b,e,packed[(64+key+rc())*36+k]);}acc=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,acc);}
  for(uint e=0;e<8;e++){uint q=first+gr()*8+e,k=key+rc();float score=acc[e]+w[4*channels*channels+head*4096+q*64+k],affine=clampf(score*.044921875f+1.30078125f,1.03125f,1.5693359375f);uint ah=(bits(affine)>>13)-0x1c000u;ushort hb=static_cast<ushort>(((ah<<5)+0x8000u)&65535u);ex[q*66+k]=__builtin_bit_cast(_Float16,hb);}
 }
 sync_window();
 // MH production partial0 sums keys0..15,32..47; partial1 sums16..31,48..63.
 // Keep this distinct from C32 FAST4's sequential64-key accumulator.
 f8 sums[2];for(uint side=0;side<2;side++){f8 sum{};for(uint half=0;half<2;half++){h8 a{},ones{};for(uint e=0;e<8;e++){uint k=side*16+half*32+gr()*8+e;a[e]=ex[(first+rc())*66+k];ones[e]=(_Float16)1.f;}sum=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(a,ones,sum);}sums[side]=sum;}
 // Q/K are dead; probability64x68 occupies4352 of their4608 bytes. V starts4608.
 for(uint key=0;key<64;key+=16)for(uint e=0;e<8;e++){uint row=first+gr()*8+e,k=key+rc();float inv=1.f/(sums[0][e]+sums[1][e]);packed[row*68+k]=static_cast<unsigned char>(fp8(float(ex[row*66+k])*inv));}
 sync_window();
 for(uint col=0;col<32;col+=16){f8 acc{};for(uint kt=0;kt<4;kt++){i2 a{},b{};for(uint e=0;e<8;e++){uint k=kt*16+gr()*8+e;put_bits(a,e,packed[(first+rc())*68+k]);put_bits(b,e,packed[(128+k)*36+col+rc()]);}acc=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,acc);}for(uint e=0;e<8;e++){uint p=raster(win,first+gr()*8+e,width);avbytes[(first+gr()*8+e)*68+head*32+col+rc()]=static_cast<unsigned char>(fp8(F(acc[e])));}}

 sync_window();
 f8 result[2]{};
 for(uint j=0;j<2;j++){uint col=head*32+j*16+rc();float remain=w[4*64*64+2*4096+2+col];for(uint part=0;part<3;part++){float component;if(absf(remain)<.015625f){float x=absf(remain)*512.f;uint q=uint(x);float r=x-float(q);q+=uint(r>.5f||(r==.5f&&(q&1)));q=q>7?7:q;component=(remain<0?-1.f:1.f)*float(q)/512.f;}else component=F(remain);remain-=component;for(uint e=0;e<8;e++){uint p=raster(win,first+gr()*8+e,width);float x=__builtin_amdgcn_cvt_f32_fp8(int(fp8(feature[p*64+col])),0);for(uint half=0;half<2;half++)result[j][e]=__builtin_fmaf(x,half==(col%32)/16?component:0.f,result[j][e]);}}}
 const uint*pw=reinterpret_cast<const uint*>(w);
 for(uint k=0;k<64;k+=16){i2 a{};__builtin_memcpy(&a,avbytes+(first+rc())*68+k+gr()*8,8);for(uint j=0;j<2;j++){uint col=head*32+j*16+rc(),off=3*64*64+(col*64+k+gr()*8)/4;i2 b={int(pw[off]),int(pw[off+1])};result[j]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,result[j]);}}
 for(uint j=0;j<2;j++)for(uint e=0;e<8;e++){uint p=raster(win,first+gr()*8+e,width),col=head*32+j*16+rc(),dest=p*64+col;if(cropw){uint x=p%width,y=p/width;if(x<sx||y<sy||x>=sx+cropw||y>=sy+croph)continue;dest=((y-sy)*cropw+x-sx)*64+col;}float v=result[j][e];out[dest]=post==3?Hrtz(v):post==0?F(Hrtz(v)):F(v);}
}
