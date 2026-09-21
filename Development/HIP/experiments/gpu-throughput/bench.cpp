#include "../../hip_api.h"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstring>
using namespace hip_probe;
int main(int argc,char**argv){try{
 if(argc!=2&&argc!=3&&argc!=5)throw std::runtime_error("usage: bench.exe MODULE.hsaco [KIND [ACC GROUPS]]");
 Api a;a.Check(a.hipInit(0),"init");a.Check(a.hipSetDevice(0),"device");auto prop=a.Properties(0);
 printf("device=%s arch=%s MPs=%d warp=%d max_threads_MP=%d shared_MP=%zu\n",prop.name,prop.gcnArchName,prop.multiProcessorCount,prop.warpSize,prop.maxThreadsPerMultiProcessor,prop.sharedMemPerMultiprocessor);
 if(prop.warpSize!=32)throw std::runtime_error("wave32 required");
 Handle module{},stream{},begin{},end{};a.Check(a.LoadModule(&module,argv[1]),"module");a.Check(a.hipStreamCreate(&stream),"stream");a.Check(a.hipEventCreate(&begin),"event begin");a.Check(a.hipEventCreate(&end),"event end");
 void*in8{},*in16{},*in32{},*out{};std::vector<unsigned char>x8(512,0x18);std::vector<unsigned short>x16(512,0x2c00);std::vector<float>x32(128,1.f/16.f);
 a.Check(a.hipMalloc(&in8,x8.size()),"in8");a.Check(a.hipMalloc(&in16,x16.size()*2),"in16");a.Check(a.hipMalloc(&in32,x32.size()*4),"in32");a.Check(a.hipMalloc(&out,1024*256*4),"output");
 a.Check(a.hipMemcpy(in8,x8.data(),x8.size(),1),"upload8");a.Check(a.hipMemcpy(in16,x16.data(),x16.size()*2,1),"upload16");a.Check(a.hipMemcpy(in32,x32.data(),x32.size()*4,1),"upload32");
 FILE*csv=fopen("timing.csv","wb");if(!csv)throw std::runtime_error("csv");
 fprintf(csv,"kind,accumulators,groups,iterations,sample,launches,start_tick,end_tick,wall_ms,event_ms,flops_per_launch,wall_tflops,event_tflops\n");
 using Occ=int(*)(int*,Handle,int,size_t);Occ occupancy{};a.Load(occupancy,"hipModuleOccupancyMaxActiveBlocksPerMultiprocessor");
 double batch_ms=std::getenv("GPU_THROUGHPUT_BATCH_MS")?std::stod(std::getenv("GPU_THROUGHPUT_BATCH_MS")):150.;
 unsigned sample_count=std::getenv("GPU_THROUGHPUT_SAMPLES")?unsigned(std::stoul(std::getenv("GPU_THROUGHPUT_SAMPLES"))):5;
 if(batch_ms<50||batch_ms>1000||sample_count<3||sample_count>15)throw std::runtime_error("sample parameters");
 unsigned configs=0;
 for(const char*kind:{"fp8","fp16","fp32","fp32d"})for(unsigned n:{1u,2u,4u,8u,16u}){
  if(argc>=3&&std::string(kind)!=argv[2])continue;if(argc==5&&n!=unsigned(std::stoul(argv[3])))continue;if(std::string(kind)=="fp32d"&&n==1)continue;
  const bool vector=std::string(kind).rfind("fp32",0)==0;std::string name=std::string(kind)+"_"+std::to_string(n);Handle fn{};a.Check(a.hipModuleGetFunction(&fn,module,name.c_str()),"function");int resident=0;a.Check(occupancy(&resident,fn,256,0),"occupancy");
  printf("RESOURCE kernel=%s blocks_per_MP=%d resident_waves_bound=%d\n",name.c_str(),resident,resident*8);
  void*input=vector?in32:std::string(kind)=="fp16"?in16:in8;
  for(unsigned groups:{64u,256u,1024u}){
   if(argc==5&&groups!=unsigned(std::stoul(argv[4])))continue;
   unsigned iterations=vector?8192u:2048u;void*args[]={&input,&out,&iterations};
   auto launch=[&](){a.Check(a.hipModuleLaunchKernel(fn,groups,1,1,256,1,1,0,stream,args,nullptr),"launch");};
   auto check=[&](){std::vector<float>actual(size_t(groups)*256);a.Check(a.hipMemcpy(actual.data(),out,actual.size()*4,2),"readback");double steps=double(iterations)*16,expected=vector?n*(n+1)/2.0+n*steps/256.0:8*(n*(n+1)/2.0+n*steps/16.0);for(float x:actual)if(!std::isfinite(x)||x!=float(expected))throw std::runtime_error("checksum mismatch "+name+" expected="+std::to_string(expected)+" actual="+std::to_string(x));};
   // Known exact binary fractions: validate short loops and the sustained loop.
   unsigned saved=iterations;iterations=3;launch();a.Check(a.hipStreamSynchronize(stream),"short sync");check();iterations=saved;
   auto pilot=std::chrono::steady_clock::now();launch();a.Check(a.hipStreamSynchronize(stream),"pilot sync");double one=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-pilot).count();check();
   unsigned launches=std::clamp(unsigned(std::ceil(batch_ms/one)),2u,2000u);
   for(unsigned i=0;i<launches;i++)launch();a.Check(a.hipStreamSynchronize(stream),"warm sync");
   double flops=vector?double(groups)*256*n*16*iterations*2:double(groups)*8*n*16*iterations*8192;
   std::vector<double>rates;
   for(unsigned sample=0;sample<sample_count;sample++){
    a.Check(a.hipStreamSynchronize(stream),"pre drain");auto tick=GetTickCount64();auto t=std::chrono::steady_clock::now();a.Check(a.hipEventRecord(begin,stream),"begin");
    for(unsigned i=0;i<launches;i++)launch();a.Check(a.hipEventRecord(end,stream),"end");a.Check(a.hipStreamSynchronize(stream),"sample sync");
    double ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-t).count();auto stop=GetTickCount64();float ems=0;a.Check(a.hipEventElapsedTime(&ems,begin,end),"elapsed");
    if(!(ems>0)||!std::isfinite(ems))throw std::runtime_error("invalid event time");double walltf=flops*launches/(ms*1e9),eventtf=flops*launches/(double(ems)*1e9);rates.push_back(walltf);
    fprintf(csv,"%s,%u,%u,%u,%u,%u,%llu,%llu,%.9f,%.9f,%.0f,%.9f,%.9f\n",kind,n,groups,iterations,sample,launches,tick,stop,ms,double(ems),flops,walltf,eventtf);fflush(csv);
   }
   check();std::sort(rates.begin(),rates.end());printf("RESULT kind=%s accum=%u groups=%u wall_median_TFLOPS=%.3f launches=%u checksum=PASS\n",kind,n,groups,rates[rates.size()/2],launches);fflush(stdout);configs++;
  }
 }
 fclose(csv);if(!configs)throw std::runtime_error("no matching configuration");printf("PASS configurations=%u\n",configs);a.hipFree(in8);a.hipFree(in16);a.hipFree(in32);a.hipFree(out);a.hipEventDestroy(begin);a.hipEventDestroy(end);a.hipStreamDestroy(stream);a.hipModuleUnload(module);return 0;
}catch(const std::exception&e){fprintf(stderr,"FAIL %s\n",e.what());return 1;}}
