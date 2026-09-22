// Reuse the half bits already produced by RTZ instead of f32->f16 again.
DEV void retain_encode(float x,_Float16&saved,float&rounded,uint&byte){
 uint h;asm("v_cvt_pkrtz_f16_f32 %0, %1, %1" : "=v"(h) : "v"(x));
 union{uint u;_Float16 h[2];}v;v.u=h;saved=v.h[0];
 asm("v_cvt_f32_f16 %0, %1" : "=v"(rounded) : "v"(h));
 byte=fp8(rounded);
}
KERNEL void retain_primitive(const float*in,uint*out,uint n){
 uint i=bid()*256+__builtin_amdgcn_workitem_id_x();if(i>=n)return;
 float a=Hrtz(in[i]),b;_Float16 saved;uint byte;
 retain_encode(in[i],saved,b,byte);
 union{_Float16 h;unsigned short u;}ha,hb;ha.h=(_Float16)a;hb.h=saved;
 out[i*6]=bits(a);out[i*6+1]=ha.u;out[i*6+2]=fp8(a);
 out[i*6+3]=bits(b);out[i*6+4]=hb.u;out[i*6+5]=byte;
}
