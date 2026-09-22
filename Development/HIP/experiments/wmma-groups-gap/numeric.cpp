#include "../../hip_api.h"
#include <vector>
#include <cstring>
using namespace hip_probe;
int main(int argc,char**argv){try{
 if(argc!=2)throw std::runtime_error("module");Api api;api.Check(api.hipInit(0),"init");api.Check(api.hipSetDevice(0),"device");Handle mod{};api.Check(api.LoadModule(&mod,argv[1]),"module");
 unsigned state=97;auto next=[&](){state=1664525*state+1013904223;return int((state>>16)%3)-1;};auto code=[](int x){return (unsigned char)(x<0?0x98:x>0?0x18:0);};
 std::vector<signed char>a(640*1024),b(4096*1024);for(auto&v:a)v=next();for(auto&v:b)v=next();std::vector<unsigned char>ap(a.size()),bp(b.size());
 for(unsigned row=0;row<640;row++)for(unsigned k=0;k<1024;k++){unsigned kt=k/16*16,g=(k%16)/8,e=k%8;ap[row*1024+kt/32*32+g*16+(kt%32)/16*8+e]=code(a[row*1024+k]);}
 for(unsigned row=0;row<4096;row++)for(unsigned k=0;k<1024;k++){unsigned kt=k/16*16,g=(k%16)/8,e=k%8;bp[row/16*16384+kt/32*512+(g*16+row%16)*16+(kt%32)/16*8+e]=code(b[row*1024+k]);}
 void*A{},*B{},*O{};std::vector<unsigned>canary(2560*32,0x7fc00000u);api.Check(api.hipMalloc(&A,ap.size()),"A");api.Check(api.hipMalloc(&B,bp.size()),"B");api.Check(api.hipMalloc(&O,canary.size()*4),"O");api.Check(api.hipMemcpy(A,ap.data(),ap.size(),1),"upload A");api.Check(api.hipMemcpy(B,bp.data(),bp.size(),1),"upload B");
 auto word=[](const std::vector<unsigned char>&v,size_t p){return unsigned(v[p])|(unsigned(v[p+1])<<8)|(unsigned(v[p+2])<<16)|(unsigned(v[p+3])<<24);};unsigned as=0,bs=0,rounds=16;void*args[]={&A,&B,&O,&as,&bs,&rounds};
 for(const char*kind:{"mat","load"})for(unsigned W:{1u,2u,4u,8u})for(unsigned mapped=0;mapped<(W==1?1u:2u);mapped++){
  std::string name=std::string(kind)+"_"+(mapped?"m":"i")+std::to_string(W);auto ref=canary;
  for(unsigned local=0;local<W;local++){unsigned wave=mapped?local*64:local,first=wave/64*16,col=wave%64*64;
   for(unsigned lane=0;lane<32;lane++){float value;
    if(std::string(kind)=="mat"){int total=0;for(unsigned n=0;n<4;n++)for(unsigned e=0;e<8;e++){unsigned row=first+lane/16*8+e,c=col+n*16+lane%16;for(unsigned k=0;k<1024;k++)total+=int(a[row*1024+k])*int(b[c*1024+k]);}value=80.f+float(total)/256.f;}
    else{unsigned total=0,r=lane%16,g=lane/16;for(unsigned k=0;k<1024;k+=32){for(unsigned e=0;e<4;e++)total^=word(ap,(first+r)*1024+k+g*16+e*4);for(unsigned n=0;n<4;n++){unsigned row=col+n*16+r;for(unsigned e=0;e<4;e++)total^=word(bp,row/16*16384+k/32*512+(g*16+row%16)*16+e*4);}}value=float(total)+208.f;}
    std::memcpy(&ref[wave*32+lane],&value,4);
   }
  }
  api.Check(api.hipMemcpy(O,canary.data(),canary.size()*4,1),"canary");Handle fn{};api.Check(api.hipModuleGetFunction(&fn,mod,name.c_str()),"fn");api.Check(api.hipModuleLaunchKernel(fn,1,1,1,W*32,1,1,0,nullptr,args,nullptr),"launch");api.Check(api.hipDeviceSynchronize(),"sync");std::vector<unsigned>actual(ref.size());api.Check(api.hipMemcpy(actual.data(),O,actual.size()*4,2),"read");size_t bad=0;for(size_t i=0;i<ref.size();i++)bad+=actual[i]!=ref[i];printf("NUMERIC %s active_lanes=%u checked_words=%llu bad=%llu\n",name.c_str(),W*32,(unsigned long long)ref.size(),(unsigned long long)bad);if(bad)throw std::runtime_error("numeric/map/canary mismatch");
 }
 api.hipFree(A);api.hipFree(B);api.hipFree(O);api.hipModuleUnload(mod);return 0;
}catch(const std::exception&e){fprintf(stderr,"FAIL %s\n",e.what());return 1;}}
