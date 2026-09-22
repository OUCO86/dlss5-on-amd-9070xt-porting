#pragma clang fp contract(off)
#pragma clang fp reassociate(off)
typedef unsigned uint;
typedef unsigned char u8;
using i2=int __attribute__((ext_vector_type(2)));
using f8=float __attribute__((ext_vector_type(8)));
#define DEV __attribute__((device)) __attribute__((always_inline))
#define KERNEL extern "C" __attribute__((global)) __attribute__((amdgpu_flat_work_group_size(32,32)))
DEV uint lane(){return __builtin_amdgcn_workitem_id_x();}
DEV uint block(){return __builtin_amdgcn_workgroup_id_x();}
DEV uint boffset(uint row,uint k){return ((row/16)*32+k/32)*512+(((k%32)/16*2+(lane()>>4))*16+row%16)*8;}
template<bool Volatile> DEV i2 fetch(const u8*p){
 if constexpr(Volatile)return *reinterpret_cast<const volatile i2*>(p);
 else return *reinterpret_cast<const i2*>(p);
}
template<int N> DEV void resident(const u8*A,const u8*B,float*out,uint rounds){
 uint first=block()/64*16,col=block()%64*64,r=lane()&15,g=lane()>>4;
 i2 a=fetch<false>(A+(first+r)*1024+g*8),b[N];f8 c[N];
 #pragma unroll
 for(uint j=0;j<N;j++){b[j]=fetch<false>(B+boffset((col+j*16+r)%4096,0));float x=float(j+1);c[j]=f8{x,x,x,x,x,x,x,x};}
 #pragma clang loop unroll(disable)
 for(uint it=0;it<rounds;it++){
  #pragma unroll
  for(uint u=0;u<16/N;u++){
   #pragma unroll
   for(uint j=0;j<N;j++)c[j]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b[j],c[j]);
  }
 }
 float sum=0;
 #pragma unroll
 for(uint j=0;j<N;j++){
  #pragma unroll
  for(uint e=0;e<8;e++)sum+=c[j][e];
 }
 out[block()*32+lane()]=sum;
}
template<bool Volatile,uint AddressMode=0> DEV void feed(const u8*A,const u8*B,float*out,uint astride,uint bstride,uint rounds){
 uint first=block()/64*16,col=block()%64*64,r=lane()&15,g=lane()>>4;f8 c[4];
 #pragma unroll
 for(uint j=0;j<4;j++){float x=float(j+1);c[j]=f8{x,x,x,x,x,x,x,x};}
 #pragma clang loop unroll(disable)
 for(uint it=0;it<rounds;it++){
  #pragma unroll 4
  for(uint u=0;u<4;u++){
   uint step=it*4+u;
   uint ka=AddressMode==1?((step*16)&astride):AddressMode==2?step*16:step*astride;
   uint kb=AddressMode==1?((step*16)&bstride):AddressMode==2?step*16:step*bstride;
   i2 a=fetch<Volatile>(A+(first+r)*1024+ka+g*8);
   #pragma unroll
   for(uint j=0;j<4;j++){
    i2 b=fetch<Volatile>(B+boffset(col+j*16+r,kb));
    c[j]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,c[j]);
   }
  }
 }
 float sum=0;
 #pragma unroll
 for(uint j=0;j<4;j++){
  #pragma unroll
  for(uint e=0;e<8;e++)sum+=c[j][e];
 }
 out[block()*32+lane()]=sum;
}
#define REG(N) KERNEL void resident##N(const u8*a,const u8*b,float*c,uint as,uint bs,uint rounds){resident<N>(a,b,c,rounds);}
REG(1)
REG(2)
REG(4)
REG(8)
REG(16)
KERNEL void plain4(const u8*a,const u8*b,float*c,uint as,uint bs,uint rounds){feed<false>(a,b,c,as,bs,rounds);}
KERNEL void volatile4(const u8*a,const u8*b,float*c,uint as,uint bs,uint rounds){feed<true>(a,b,c,as,bs,rounds);}

KERNEL void masked4(const u8*a,const u8*b,float*c,uint am,uint bm,uint rounds){feed<false,1>(a,b,c,am,bm,rounds);}
KERNEL void model4(const u8*a,const u8*b,float*c,uint am,uint bm,uint rounds){feed<false,2>(a,b,c,am,bm,rounds);}

DEV uint pitched_offset(uint row,uint k,uint pitch){return (row/16)*pitch+(k/32)*512+(((k%32)/16*2+(lane()>>4))*16+row%16)*8;}
template<bool Volatile,uint AddressMode=0> DEV void feed_pitch(const u8*A,const u8*B,float*out,uint astride,uint bstride,uint rounds,uint pitch){
 uint first=block()/64*16,col=block()%64*64,r=lane()&15,g=lane()>>4;f8 c[4];
 #pragma unroll
 for(uint j=0;j<4;j++){float x=float(j+1);c[j]=f8{x,x,x,x,x,x,x,x};}
 #pragma clang loop unroll(disable)
 for(uint it=0;it<rounds;it++){
  #pragma unroll 4
  for(uint u=0;u<4;u++){
   uint step=it*4+u;
   uint ka=AddressMode==1?((step*16)&astride):AddressMode==2?step*16:step*astride;
   uint kb=AddressMode==1?((step*16)&bstride):AddressMode==2?step*16:step*bstride;
   i2 a=fetch<Volatile>(A+(first+r)*1024+ka+g*8);
   #pragma unroll
   for(uint j=0;j<4;j++){
    i2 b=fetch<Volatile>(B+pitched_offset(col+j*16+r,kb,pitch));
    c[j]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,c[j]);
   }
  }
 }
 float sum=0;
 #pragma unroll
 for(uint j=0;j<4;j++){
  #pragma unroll
  for(uint e=0;e<8;e++)sum+=c[j][e];
 }
 out[block()*32+lane()]=sum;
}
KERNEL void pitched4(const u8*a,const u8*b,float*c,uint am,uint bm,uint rounds,uint pitch){feed_pitch<false,1>(a,b,c,am,bm,rounds,pitch);}
