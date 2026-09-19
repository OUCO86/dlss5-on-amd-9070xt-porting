typedef unsigned uint;
#define DEV __attribute__((device)) __attribute__((always_inline))
#define KERNEL extern "C" __attribute__((global))
template<uint C,bool Mapped> DEV uint ffn_input8_word(const unsigned char*in,uint p,uint c,uint width,uint height,uint workw,uint sx,uint sy){
 uint index=p*C+c;bool ok=true;
 if constexpr(Mapped){int x=int(p%workw)-int(sx),y=int(p/workw)-int(sy);ok=x>=0&&y>=0&&x<int(width)&&y<int(height);uint xi=ok?uint(x):0u,yi=ok?uint(y):0u;index=(yi*width+xi)*C+c;}
 uint word;__builtin_memcpy(&word,in+index,4);return ok?word:0u;
}
template<uint C,bool Mapped> DEV float ffn_input8_nb(const unsigned char*in,uint p,uint c,uint width,uint height,uint workw,uint sx,uint sy){if constexpr(Mapped){int x=int(p%workw)-int(sx),y=int(p/workw)-int(sy);bool ok=x>=0&&y>=0&&x<int(width)&&y<int(height);uint xi=ok?uint(x):0u,yi=ok?uint(y):0u;float v=__builtin_amdgcn_cvt_f32_fp8(int(in[(yi*width+xi)*C+c]),0);return ok?v:0.f;}return __builtin_amdgcn_cvt_f32_fp8(int(in[p*C+c]),0);}
DEV uint pack4(float a,float b,float c,float d){uint lo=uint(__builtin_amdgcn_cvt_pk_fp8_f32(a,b,0,false));uint hi=uint(__builtin_amdgcn_cvt_pk_fp8_f32(c,d,0,false));return (lo&65535u)|((hi&65535u)<<16);}
KERNEL void roundtrip(uint*out){uint b=__builtin_amdgcn_workitem_id_x();float x=__builtin_amdgcn_cvt_f32_fp8(int(b),0);out[b]=uint(__builtin_amdgcn_cvt_pk_fp8_f32(x,x,0,false))&255u;}
template<uint C> DEV void one(const unsigned char*in,uint*out,uint i){uint p=i/(C/4),k=(i%(C/4))*4;out[2*i]=ffn_input8_word<C,true>(in,p,k,13,11,24,4,5);out[2*i+1]=pack4(ffn_input8_nb<C,true>(in,p,k,13,11,24,4,5),ffn_input8_nb<C,true>(in,p,k+1,13,11,24,4,5),ffn_input8_nb<C,true>(in,p,k+2,13,11,24,4,5),ffn_input8_nb<C,true>(in,p,k+3,13,11,24,4,5));}
KERNEL void stage(const unsigned char*in,uint*out,uint c,uint n){uint i=__builtin_amdgcn_workgroup_id_x()*256+__builtin_amdgcn_workitem_id_x();if(i>=n)return;if(c==64)one<64>(in,out,i);else if(c==128)one<128>(in,out,i);else one<256>(in,out,i);}
