KERNEL void pair_primitive(const float*in,uint*out,uint n){
 uint i=bid()*256+__builtin_amdgcn_workitem_id_x();if(i>=n)return;
 float x=in[i],y=in[n-1-i],a,b;uint bytes;
 // Baseline and three candidates: rounded f32 bits, saved half bits, FP8 bytes.
 #pragma unroll
 for(uint mode=0;mode<4;mode++){
  if(mode==0)pair_encode<0>(x,y,a,b,bytes);
  if(mode==1)pair_encode<1>(x,y,a,b,bytes);
  if(mode==2)pair_encode<2>(x,y,a,b,bytes);
  if(mode==3)pair_encode<3>(x,y,a,b,bytes);
  union{_Float16 h;unsigned short u;}ha,hb;ha.h=(_Float16)a;hb.h=(_Float16)b;
  out[i*16+mode*4]=bits(a);out[i*16+mode*4+1]=bits(b);
  out[i*16+mode*4+2]=uint(ha.u)|(uint(hb.u)<<16);out[i*16+mode*4+3]=bytes;
 }
}
