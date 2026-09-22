KERNEL void pair128_loadonly(const u8*A,const u8*B,float*out,uint as,uint bs,uint rounds){
 uint first=block()/64*16,col=block()%64*64,r=lane()&15,total=0;
 #pragma clang loop unroll(disable)
 for(uint it=0;it<rounds;it++){
  #pragma unroll 2
  for(uint u=0;u<2;u++){uint k=(it*2+u)*32;i4 av=*reinterpret_cast<const i4*>(A+pair_a(first+r,k));
   #pragma unroll
   for(uint e=0;e<4;e++)total^=uint(av[e]);
   #pragma unroll
   for(uint j=0;j<4;j++){i4 bv=*reinterpret_cast<const i4*>(B+pair_b(col+j*16+r,k));
    #pragma unroll
    for(uint e=0;e<4;e++)total^=uint(bv[e]);
   }
  }
 }
 out[block()*32+lane()]=float(total)+208.f;
}
