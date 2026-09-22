// bit 0: pair RTZ conversion; bit 1: pair FP8 conversion.
// Keep both float-to-half residual stores exactly as the production source.
template<uint Mode>
DEV void pair_encode(float x,float y,float&a,float&b,uint&bytes){
 if constexpr(Mode&1){uint h;
  asm("v_cvt_pkrtz_f16_f32 %0, %1, %2" : "=v"(h) : "v"(x),"v"(y));
  asm("v_cvt_f32_f16 %0, %1" : "=v"(a) : "v"(h));
  uint upper=h>>16;asm("v_cvt_f32_f16 %0, %1" : "=v"(b) : "v"(upper));
 }else{a=Hrtz(x);b=Hrtz(y);}
 if constexpr(Mode&2){
  float ca=__builtin_fminf(__builtin_fmaxf(a,-448.f),448.f);
  float cb=__builtin_fminf(__builtin_fmaxf(b,-448.f),448.f);
  bytes=uint(__builtin_amdgcn_cvt_pk_fp8_f32(ca,cb,0,false))&65535u;
 }else bytes=fp8(a)|(fp8(b)<<8);
}
