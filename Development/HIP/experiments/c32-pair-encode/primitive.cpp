#include "hip_api.h"
#include <vector>
#include <cstring>
#include <cstdio>
using namespace hip_probe;
static float f32(unsigned u){float x;memcpy(&x,&u,4);return x;}
static unsigned half_float_bits(unsigned h){
 unsigned sign=(h&32768u)<<16,e=(h>>10)&31,m=h&1023u;
 if(e==31)return sign|0x7f800000u|(m<<13);
 if(e)return sign|((e+112)<<23)|(m<<13);
 if(!m)return sign;
 unsigned shift=0;while(!(m&1024)){m<<=1;shift++;}
 return sign|((113-shift)<<23)|((m&1023)<<13);
}
int main(int argc,char**argv){try{
 if(argc<2||argc>3)throw std::runtime_error("module required");
 bool retain=argc==3;
 std::vector<float>input;unsigned state=123456789;
 // All half values, both adjacent f32 bit patterns, including zero/Inf/NaN.
 for(unsigned h=0;h<65536;h++){unsigned b=half_float_bits(h);input.push_back(f32(b));input.push_back(f32(b-1));input.push_back(f32(b+1));}
 // Unfiltered f32 bit patterns include subnormal, overflow and nonfinite inputs.
 for(unsigned i=0;i<1000000;i++){state=1664525*state+1013904223;input.push_back(f32(state));}
 Api api;api.Check(api.hipInit(0),"init");api.Check(api.hipSetDevice(0),"device");Handle mod{},fn{};
 api.Check(api.hipModuleLoad(&mod,argv[1]),"module");api.Check(api.hipModuleGetFunction(&fn,mod,retain?"retain_primitive":"pair_primitive"),"function");
 void*in{},*out{};unsigned n=input.size();api.Check(api.hipMalloc(&in,size_t(n)*4),"in");api.Check(api.hipMalloc(&out,size_t(n)*64),"out");
 api.Check(api.hipMemcpy(in,input.data(),size_t(n)*4,1),"upload");void*args[]={&in,&out,&n};
 api.Check(api.hipModuleLaunchKernel(fn,(n+255)/256,1,1,256,1,1,0,nullptr,args,nullptr),"launch");api.Check(api.hipDeviceSynchronize(),"sync");
 std::vector<unsigned>r(size_t(n)*16);api.Check(api.hipMemcpy(r.data(),out,r.size()*4,2),"read");size_t total=0;
 if(retain){for(unsigned i=0;i<n;i++)for(unsigned k=0;k<3;k++)if(r[i*6+k]!=r[i*6+3+k]){
  if(total<6)printf("retain i=%u component=%u input=%a ref=%08x got=%08x\n",i,k,input[i],r[i*6+k],r[i*6+3+k]);total++;
 }printf("retain count=%u components=3 bitdiff=%llu\n",n,(unsigned long long)total);
 }else{
 for(unsigned mode=1;mode<4;mode++){size_t bad=0;for(unsigned i=0;i<n;i++)for(unsigned k=0;k<4;k++)if(r[i*16+k]!=r[i*16+mode*4+k]){
  if(bad<6)printf("mode=%u i=%u component=%u x=%a y=%a ref=%08x got=%08x\n",mode,i,k,input[i],input[n-1-i],r[i*16+k],r[i*16+mode*4+k]);bad++;
 }printf("mode=%u pairs=%u components=4 bitdiff=%llu\n",mode,n,(unsigned long long)bad);total+=bad;}
}
 api.hipFree(in);api.hipFree(out);api.hipModuleUnload(mod);return total?1:0;
}catch(const std::exception&e){fprintf(stderr,"FAIL %s\n",e.what());return 1;}}
