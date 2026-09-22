#include "../../hip_api.h"
#include <vector>
#include <cmath>
using namespace hip_probe;
int main(int argc,char**argv){try{
 if(argc!=2)throw std::runtime_error("module");Api api;api.Check(api.hipInit(0),"init");api.Check(api.hipSetDevice(0),"device");Handle mod{};api.Check(api.LoadModule(&mod,argv[1]),"module");
 unsigned state=97;auto next=[&](){state=1664525*state+1013904223;return int((state>>16)%3)-1;};auto code=[](int x){return (unsigned char)(x<0?0x98:x>0?0x18:0);};
 std::vector<signed char>a(16*1024),b(4096*1024);for(auto&v:a)v=next();for(auto&v:b)v=next();
 std::vector<unsigned char>a0(a.size()),a1(a.size()),b0(b.size()),b1(b.size());
 for(unsigned row=0;row<16;row++)for(unsigned k=0;k<1024;k++){a0[row*1024+k]=code(a[row*1024+k]);unsigned kt=k/16*16,g=(k%16)/8,e=k%8;a1[row*1024+kt/32*32+g*16+(kt%32)/16*8+e]=code(a[row*1024+k]);}
 for(unsigned row=0;row<4096;row++)for(unsigned k=0;k<1024;k++){unsigned kt=k/16*16,g=(k%16)/8,e=k%8;auto v=code(b[row*1024+k]);b0[(row/16*32+kt/32)*512+(((kt%32)/16*2+g)*16+row%16)*8+e]=v;b1[row/16*16384+kt/32*512+(g*16+row%16)*16+(kt%32)/16*8+e]=v;}
 const unsigned groups=3;std::vector<float>ref(groups*32);
 for(unsigned block=0;block<groups;block++)for(unsigned lane=0;lane<32;lane++){int total=0;for(unsigned n=0;n<4;n++)for(unsigned e=0;e<8;e++){unsigned row=(lane/16)*8+e,col=block*64+n*16+lane%16;for(unsigned k=0;k<1024;k++)total+=int(a[row*1024+k])*int(b[col*1024+k]);}ref[block*32+lane]=80.f+float(total)/256.f;}
 void*A{},*B{},*O{};api.Check(api.hipMalloc(&A,a0.size()),"A");api.Check(api.hipMalloc(&B,b0.size()),"B");api.Check(api.hipMalloc(&O,ref.size()*4),"O");unsigned as=1023,bs=1023,rounds=16;void*args[]={&A,&B,&O,&as,&bs,&rounds};
 for(const char*name:{"model4","pair64","pair128","pair128_adjacent"}){bool packed=std::string(name)!="model4";auto&av=packed?a1:a0;auto&bv=packed?b1:b0;api.Check(api.hipMemcpy(A,av.data(),av.size(),1),"A upload");api.Check(api.hipMemcpy(B,bv.data(),bv.size(),1),"B upload");Handle fn{};api.Check(api.hipModuleGetFunction(&fn,mod,name),"fn");api.Check(api.hipModuleLaunchKernel(fn,groups,1,1,32,1,1,0,nullptr,args,nullptr),"launch");api.Check(api.hipDeviceSynchronize(),"sync");std::vector<float>v(ref.size());api.Check(api.hipMemcpy(v.data(),O,v.size()*4,2),"read");unsigned bad=0;for(unsigned i=0;i<v.size();i++)bad+=v[i]!=ref[i]||!std::isfinite(v[i]);printf("NUMERIC %s lanes=%u bad=%u\n",name,unsigned(v.size()),bad);if(bad)throw std::runtime_error("numeric check failed");}
 api.hipFree(A);api.hipFree(B);api.hipFree(O);api.hipModuleUnload(mod);return 0;
}catch(const std::exception&e){fprintf(stderr,"FAIL %s\n",e.what());return 1;}}
