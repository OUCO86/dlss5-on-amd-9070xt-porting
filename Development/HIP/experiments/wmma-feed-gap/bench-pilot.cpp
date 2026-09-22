#include "../../hip_api.h"
#include <vector>
#include <algorithm>
#include <chrono>
#include <cmath>
using namespace hip_probe;
struct Config{const char*name;unsigned chains,as,bs;};
int main(int argc,char**argv){try{
 if(argc!=3)throw std::runtime_error("module tokens(400/640)");unsigned tokens=std::stoul(argv[2]);if(tokens!=400&&tokens!=640)throw std::runtime_error("tokens");unsigned groups=tokens/16*64,rounds=16;
 Api api;api.Check(api.hipInit(0),"init");api.Check(api.hipSetDevice(0),"device");auto prop=api.Properties(0);printf("device=%s arch=%s MPs=%d\n",prop.name,prop.gcnArchName,prop.multiProcessorCount);
 Handle module{},stream{};api.Check(api.LoadModule(&module,argv[1]),"load");api.Check(api.hipStreamCreate(&stream),"stream");
 std::vector<unsigned char>A(size_t(tokens)*1024,0x18),B(size_t(4096)*1024,0x18);void*a{},*b{},*out{};
 api.Check(api.hipMalloc(&a,A.size()),"A");api.Check(api.hipMalloc(&b,B.size()),"B");api.Check(api.hipMalloc(&out,size_t(groups)*32*4),"out");
 api.Check(api.hipMemcpy(a,A.data(),A.size(),1),"A upload");api.Check(api.hipMemcpy(b,B.data(),B.size(),1),"B upload");
 const Config reg1{"resident1",1,0,0},reg2{"resident2",2,0,0},reg4{"resident4",4,0,0},reg8{"resident8",8,0,0},reg16{"resident16",16,0,0},plain{"plain4",4,16,16},full{"volatile4",4,16,16},fixed{"volatile4",4,0,0},fixedA{"volatile4",4,0,16},fixedB{"volatile4",4,16,0};
 struct Pair{const char*name;Config a,b;};
 std::vector<Pair>pairs={{"reg_vs_plain",reg4,plain},{"volatile_control",plain,full},{"both_address",fixed,full},{"A_address",fixedA,full},{"B_address",fixedB,full},{"chains1_4",reg1,reg4},{"chains2_4",reg2,reg4},{"chains4_8",reg4,reg8},{"chains4_16",reg4,reg16}};
 FILE*csv=fopen("timing.csv","wb");if(!csv)throw std::runtime_error("csv");fprintf(csv,"test,slot,kernel,chains,astride,bstride,tokens,rounds,launches,mean_us,tflops,bitdiff,start_ms,end_ms\n");
 for(auto pair:pairs)for(unsigned slot=0;slot<8;slot++){
  Config c=(slot%4==1||slot%4==2)?pair.b:pair.a;Handle fn{};api.Check(api.hipModuleGetFunction(&fn,module,c.name),"fn");void*args[]={&a,&b,&out,&c.as,&c.bs,&rounds};
  auto launch=[&](){api.Check(api.hipModuleLaunchKernel(fn,groups,1,1,32,1,1,0,stream,args,nullptr),"launch");};
  auto check=[&](){std::vector<float>v(size_t(groups)*32);api.Check(api.hipMemcpy(v.data(),out,v.size()*4,2),"check");float expected=8.f*(c.chains*(c.chains+1)/2.f+rounds);size_t bad=0;for(float x:v)bad+=x!=expected||!std::isfinite(x);if(bad)throw std::runtime_error("checksum mismatch "+std::string(c.name));};
  for(unsigned i=0;i<100;i++)launch();api.Check(api.hipStreamSynchronize(stream),"pilot warm");
  auto t=std::chrono::steady_clock::now();for(unsigned i=0;i<100;i++)launch();api.Check(api.hipStreamSynchronize(stream),"pilot");double single=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-t).count()/100;check();
  unsigned warm=std::clamp(unsigned(std::ceil(100./single)),100u,30000u),n=std::clamp(unsigned(std::ceil(400./single)),100u,100000u);
  for(unsigned i=0;i<warm;i++)launch();api.Check(api.hipStreamSynchronize(stream),"warm");
  auto tick=GetTickCount64();t=std::chrono::steady_clock::now();for(unsigned i=0;i<n;i++)launch();api.Check(api.hipStreamSynchronize(stream),"timed");
  double us=std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-t).count()/n;auto end=GetTickCount64();check();
  double flops=double(groups)*rounds*16*8192,tf=flops/(us*1e6);
  fprintf(csv,"%s,%u,%s,%u,%u,%u,%u,%u,%u,%.9f,%.9f,0,%llu,%llu\n",pair.name,slot,c.name,c.chains,c.as,c.bs,tokens,rounds,n,us,tf,(unsigned long long)tick,(unsigned long long)end);fflush(csv);
  printf("FEED %s slot=%u %s Astep=%u Bstep=%u us=%.3f TF=%.3f check=PASS\n",pair.name,slot,c.name,c.as,c.bs,us,tf);fflush(stdout);
 }
 fclose(csv);api.hipFree(a);api.hipFree(b);api.hipFree(out);api.hipStreamDestroy(stream);api.hipModuleUnload(module);return 0;
}catch(const std::exception&e){fprintf(stderr,"FAIL %s\n",e.what());return 1;}}
