#pragma clang fp contract(off)
#pragma clang fp reassociate(off)
typedef unsigned uint;
typedef int i2 __attribute__((ext_vector_type(2)));
typedef _Float16 h8 __attribute__((ext_vector_type(8)));
typedef float f8 __attribute__((ext_vector_type(8)));
#define DEV __attribute__((device)) __attribute__((always_inline))
#define KERNEL extern "C" __attribute__((global)) __attribute__((amdgpu_flat_work_group_size(256,256)))
// Runtime-loaded operands. Different initial accumulators prevent common-expression merging.
// Every component remains live via the final checksum. No memory traffic in the arithmetic loop.
template<int N,bool Half> DEV void matrix(const void*input,float*out,uint iterations){
 uint lane=__builtin_amdgcn_workitem_id_x()%32;
 i2 a8{},b8{};h8 a16{},b16{};
 if constexpr(Half){a16=reinterpret_cast<const h8*>(input)[lane];b16=reinterpret_cast<const h8*>(input)[32+lane];}
 else{a8=reinterpret_cast<const i2*>(input)[lane];b8=reinterpret_cast<const i2*>(input)[32+lane];}
 f8 c[N];
 #pragma unroll
 for(int j=0;j<N;j++)c[j]=f8{float(j+1),float(j+1),float(j+1),float(j+1),float(j+1),float(j+1),float(j+1),float(j+1)};
 #pragma clang loop unroll(disable)
 for(uint it=0;it<iterations;it++){
  #pragma unroll
  for(int u=0;u<16;u++){
   #pragma unroll
   for(int j=0;j<N;j++){
    if constexpr(Half)c[j]=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(a16,b16,c[j]);
    else c[j]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a8,b8,c[j]);
   }
  }
 }
 float sum=0;
 #pragma unroll
 for(int j=0;j<N;j++){
  #pragma unroll
  for(int e=0;e<8;e++)sum+=c[j][e];
 }
 out[__builtin_amdgcn_workgroup_id_x()*256+__builtin_amdgcn_workitem_id_x()]=sum;
}
template<int N,bool Separate=false> DEV void vector_fma(const float*input,float*out,uint iterations){
 uint lane=__builtin_amdgcn_workitem_id_x()%32;float a=input[lane],b=input[32+lane],c[N];
 float a1=Separate?input[64+lane]:a,b1=Separate?input[96+lane]:b;
 #pragma unroll
 for(int j=0;j<N;j++)c[j]=float(j+1);
 #pragma clang loop unroll(disable)
 for(uint it=0;it<iterations;it++){
  #pragma unroll
  for(int u=0;u<16;u++){
   #pragma unroll
   for(int j=0;j<N;j++){if constexpr(Separate)c[j]=(j&1)?__builtin_fmaf(a1,b1,c[j]):__builtin_fmaf(a,b,c[j]);else c[j]=__builtin_fmaf(a,b,c[j]);}
  }
 }
 float sum=0;
 #pragma unroll
 for(int j=0;j<N;j++)sum+=c[j];
 out[__builtin_amdgcn_workgroup_id_x()*256+__builtin_amdgcn_workitem_id_x()]=sum;
}
#define ENTRY(N) \
 KERNEL void fp8_##N(const void*i,float*o,uint n){matrix<N,false>(i,o,n);} \
 KERNEL void fp16_##N(const void*i,float*o,uint n){matrix<N,true>(i,o,n);} \
 KERNEL void fp32_##N(const float*i,float*o,uint n){vector_fma<N>(i,o,n);}
ENTRY(1)
ENTRY(2)
ENTRY(4)
ENTRY(8)
ENTRY(16)

// Separate runtime operand pairs make bank-compatible dual-issue scheduling possible.
KERNEL void fp32d_2(const float*i,float*o,uint n){vector_fma<2,true>(i,o,n);}
KERNEL void fp32d_4(const float*i,float*o,uint n){vector_fma<4,true>(i,o,n);}
KERNEL void fp32d_8(const float*i,float*o,uint n){vector_fma<8,true>(i,o,n);}
KERNEL void fp32d_16(const float*i,float*o,uint n){vector_fma<16,true>(i,o,n);}
