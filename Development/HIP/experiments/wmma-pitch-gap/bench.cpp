#include "../../hip_api.h"
#include <vector>
#include <algorithm>
#include <chrono>
#include <cmath>
using namespace hip_probe;
struct Config{const char*name;unsigned chains,as,bs,pitch=16384;};
int main(int argc,char**argv){try{
 if(argc!=3)throw std::runtime_error("module tokens(400/640)");unsigned tokens=std::stoul(argv[2]);if(tokens!=400&&tokens!=640)throw std::runtime_error("tokens");unsigned groups=tokens/16*64,rounds=16;
 Api api;api.Check(api.hipInit(0),"init");api.Check(api.hipSetDevice(0),"device");auto prop=api.Properties(0);printf("device=%s arch=%s MPs=%d\n",prop.name,prop.gcnArchName,prop.multiProcessorCount);
 Handle module{},stream{};api.Check(api.LoadModule(&module,argv[1]),"load");api.Check(api.hipStreamCreate(&stream),"stream");
 std::vector<unsigned char>A(size_t(tokens)*1024,0x18),B(size_t(256)*17408,0x18);void*a{},*b{},*out{};
 api.Check(api.hipMalloc(&a,A.size()),"A");api.Check(api.hipMalloc(&b,B.size()),"B");api.Check(api.hipMalloc(&out,size_t(groups)*32*4),"out");
 api.Check(api.hipMemcpy(a,A.data(),A.size(),1),"A upload");api.Check(api.hipMemcpy(b,B.data(),B.size(),1),"B upload");
 bool conditioned=std::getenv("GPU_GAP_CONDITION")!=nullptr;void*copyin{},*copyout{};const size_t copybytes=64u*1024u*1024u;
 if(conditioned){std::vector<unsigned char>v(copybytes,0x5a);api.Check(api.hipMalloc(&copyin,copybytes),"conditioning input");api.Check(api.hipMalloc(&copyout,copybytes),"conditioning output");api.Check(api.hipMemcpy(copyin,v.data(),copybytes,1),"conditioning upload");}
 auto condition=[&](double ms){if(!conditioned)return;auto t=std::chrono::steady_clock::now();do{api.Check(api.hipMemcpy(copyout,copyin,copybytes,3),"conditioning copy");api.Check(api.hipDeviceSynchronize(),"conditioning completion");}while(std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-t).count()<ms);};
 FILE*chunks=conditioned?fopen("chunks.csv","wb"):nullptr;if(conditioned&&!chunks)throw std::runtime_error("chunks csv");if(chunks)fprintf(chunks,"test,slot,chunk,launches,mean_us,start_ms,end_ms\n");
 printf("conditioned=%u\n",unsigned(conditioned));
 struct Pair{const char*name;Config a,b;};
 std::vector<Pair>pairs={
{"calibrate_64",{"masked4",4,1023,63},{"pitched4",4,1023,63,16384}},
{"span64_pad64",{"pitched4",4,1023,63,16384},{"pitched4",4,1023,63,16448}},
{"span64_pad128",{"pitched4",4,1023,63,16384},{"pitched4",4,1023,63,16512}},
{"span64_pad256",{"pitched4",4,1023,63,16384},{"pitched4",4,1023,63,16640}},
{"span64_pad512",{"pitched4",4,1023,63,16384},{"pitched4",4,1023,63,16896}},
{"span64_pad1024",{"pitched4",4,1023,63,16384},{"pitched4",4,1023,63,17408}},
{"calibrate_128",{"masked4",4,1023,127},{"pitched4",4,1023,127,16384}},
{"span128_pad64",{"pitched4",4,1023,127,16384},{"pitched4",4,1023,127,16448}},
{"span128_pad128",{"pitched4",4,1023,127,16384},{"pitched4",4,1023,127,16512}},
{"span128_pad256",{"pitched4",4,1023,127,16384},{"pitched4",4,1023,127,16640}},
{"span128_pad512",{"pitched4",4,1023,127,16384},{"pitched4",4,1023,127,16896}},
{"span128_pad1024",{"pitched4",4,1023,127,16384},{"pitched4",4,1023,127,17408}},
{"calibrate_1024",{"masked4",4,1023,1023},{"pitched4",4,1023,1023,16384}},
{"span1024_pad64",{"pitched4",4,1023,1023,16384},{"pitched4",4,1023,1023,16448}},
{"span1024_pad128",{"pitched4",4,1023,1023,16384},{"pitched4",4,1023,1023,16512}},
{"span1024_pad256",{"pitched4",4,1023,1023,16384},{"pitched4",4,1023,1023,16640}},
{"span1024_pad512",{"pitched4",4,1023,1023,16384},{"pitched4",4,1023,1023,16896}},
{"span1024_pad1024",{"pitched4",4,1023,1023,16384},{"pitched4",4,1023,1023,17408}}
 };
 FILE*csv=fopen("timing.csv","wb");if(!csv)throw std::runtime_error("csv");fprintf(csv,"test,slot,kernel,chains,astride,bstride,pitch,tokens,rounds,launches,mean_us,tflops,bitdiff,start_ms,end_ms\n");
 for(auto pair:pairs)for(unsigned slot=0;slot<8;slot++){
  Config c=(slot%4==1||slot%4==2)?pair.b:pair.a;Handle fn{};api.Check(api.hipModuleGetFunction(&fn,module,c.name),"fn");void*args[]={&a,&b,&out,&c.as,&c.bs,&rounds,&c.pitch};
  auto launch=[&](){api.Check(api.hipModuleLaunchKernel(fn,groups,1,1,32,1,1,0,stream,args,nullptr),"launch");};
  auto check=[&](){std::vector<float>v(size_t(groups)*32);api.Check(api.hipMemcpy(v.data(),out,v.size()*4,2),"check");float expected=8.f*(c.chains*(c.chains+1)/2.f+rounds);size_t bad=0;for(float x:v)bad+=x!=expected||!std::isfinite(x);if(bad)throw std::runtime_error("checksum mismatch "+std::string(c.name));};
  condition(200.);
  for(unsigned i=0;i<100;i++)launch();api.Check(api.hipStreamSynchronize(stream),"pilot warm");
  auto t=std::chrono::steady_clock::now();for(unsigned i=0;i<100;i++)launch();api.Check(api.hipStreamSynchronize(stream),"pilot");double single=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-t).count()/100;check();
  unsigned warm=std::clamp(unsigned(std::ceil(100./single)),100u,30000u),n=std::clamp(unsigned(std::ceil(400./single)),100u,100000u);
  for(unsigned i=0;i<warm;i++)launch();api.Check(api.hipStreamSynchronize(stream),"warm");
  auto tick=GetTickCount64();double us=0;unsigned measured=0;
  for(unsigned chunk=0;chunk<(conditioned?10u:1u);chunk++){
   condition(2.);unsigned batch=conditioned?(n+9)/10:n;auto begin=GetTickCount64();t=std::chrono::steady_clock::now();
   for(unsigned i=0;i<batch;i++)launch();api.Check(api.hipStreamSynchronize(stream),"timed");
   double elapsed=std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-t).count();auto stop=GetTickCount64();
   us+=elapsed;measured+=batch;if(chunks){fprintf(chunks,"%s,%u,%u,%u,%.9f,%llu,%llu\n",pair.name,slot,chunk,batch,elapsed/batch,(unsigned long long)begin,(unsigned long long)stop);fflush(chunks);}
  }
  us/=measured;n=measured;auto end=GetTickCount64();check();
  double flops=double(groups)*rounds*16*8192,tf=flops/(us*1e6);
  fprintf(csv,"%s,%u,%s,%u,%u,%u,%u,%u,%u,%u,%.9f,%.9f,0,%llu,%llu\n",pair.name,slot,c.name,c.chains,c.as,c.bs,c.pitch,tokens,rounds,n,us,tf,(unsigned long long)tick,(unsigned long long)end);fflush(csv);
  printf("FEED %s slot=%u %s Amask=%u Bmask=%u pitch=%u us=%.3f TF=%.3f check=PASS\n",pair.name,slot,c.name,c.as,c.bs,c.pitch,us,tf);fflush(stdout);
 }
 if(chunks)fclose(chunks);if(copyin)api.hipFree(copyin);if(copyout)api.hipFree(copyout);fclose(csv);api.hipFree(a);api.hipFree(b);api.hipFree(out);api.hipStreamDestroy(stream);api.hipModuleUnload(module);return 0;
}catch(const std::exception&e){fprintf(stderr,"FAIL %s\n",e.what());return 1;}}
