#pragma clang fp contract(off)
#pragma clang fp reassociate(off)
typedef unsigned uint;typedef unsigned char u8;typedef int i2 __attribute__((ext_vector_type(2)));typedef float f8 __attribute__((ext_vector_type(8)));
#define DEV __attribute__((device)) __attribute__((always_inline))
#define WAVE extern "C" __attribute__((global)) __attribute__((amdgpu_flat_work_group_size(32,32)))
DEV uint bits(float x){union{float f;uint u;}v;v.f=x;return v.u;}
DEV float ab(float x){return __builtin_fabsf(x);}
DEV u8 act(float x){float g=__builtin_fminf(__builtin_fmaxf(x,-4.f),4.f),q=ab(g)*(-.055908203125f)+.447265625f,p=g*q+.89453125f,v=x*p;uint z=__builtin_amdgcn_cvt_pk_fp8_f32(__builtin_fminf(__builtin_fmaxf(v,-448.f),448.f),0.f,0,false);return (bits(v)&0x7fffffffu)?u8(z):0;}
template<uint Rows,uint Tiles=4>DEV void body(const u8*x,const u8*w,u8*out,uint M){
 uint l=__builtin_amdgcn_workitem_id_x(),rc=l%16,g=l/16,bid=__builtin_amdgcn_workgroup_id_x(),first=bid/(512/(16*Tiles))*(16*Rows),col=bid%(512/(16*Tiles))*(16*Tiles);f8 acc[Rows][Tiles]{};
 for(uint k=0;k<128;k+=16){i2 a[Rows];for(uint m=0;m<Rows;m++)__builtin_memcpy(&a[m],x+(first+m*16+rc)*128+k+g*8,8);
  for(uint j=0;j<Tiles;j++){i2 b;__builtin_memcpy(&b,w+(col+j*16+rc)*128+k+g*8,8);for(uint m=0;m<Rows;m++)acc[m][j]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a[m],b,acc[m][j]);}
 }
 for(uint m=0;m<Rows;m++)for(uint j=0;j<Tiles;j++)for(uint e=0;e<8;e++)out[(first+m*16+g*8+e)*512+col+j*16+rc]=act(acc[m][j][e]);
}
WAVE void expand16(const u8*x,const u8*w,u8*out,uint M){body<1>(x,w,out,M);}
WAVE void expand32(const u8*x,const u8*w,u8*out,uint M){body<2>(x,w,out,M);}

WAVE void expand32n32(const u8*x,const u8*w,u8*out,uint M){body<2,2>(x,w,out,M);}
