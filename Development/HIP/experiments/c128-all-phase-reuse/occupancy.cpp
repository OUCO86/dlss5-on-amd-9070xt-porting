#include "../../hip_api.h"
int main(int argc,char**argv){try{
 if(argc!=2)throw std::runtime_error("usage: occupancy.exe HIP_BACKEND_ROOT");
 hip_probe::Api api;api.Check(api.hipInit(0),"init");api.Check(api.hipSetDevice(0),"device");auto p=api.Properties(0);
 printf("device=%s warpSize=%d multiprocessors=%d maxThreadsPerMP=%d sharedPerMP=%zu sharedPerCU=%zu sharedPerBlock=%zu\n",p.name,p.warpSize,p.multiProcessorCount,p.maxThreadsPerMultiProcessor,p.sharedMemPerMultiprocessor,p.maxSharedMemoryPerMultiProcessor,p.sharedMemPerBlock);
 using Fn=int(*)(int*,void*,int,size_t);Fn occupancy{};api.Load(occupancy,"hipModuleOccupancyMaxActiveBlocksPerMultiprocessor");
 struct Case{const char*dir;const char*suffix;int threads;};
 for(auto c:{Case{"post-head-shared-input-modules","",256},Case{"c128-fused-row-reuse-modules","_m32",512},Case{"c128-all-phase-reuse-modules","_m32",256},Case{"c128-hybrid-reuse-modules","_m32",512},Case{"c128-compact-reuse-modules","_m32",256}}){
  std::string path=std::string(argv[1])+"/"+c.dir+"/multihead-fast-padded-wave-packed.hsaco";void*m{},*f{};api.Check(api.LoadModule(&m,path.c_str()),"load module");
  std::string name=std::string("mh_ffn_fused_c128_project_mapped_g128_qkv_bytein_fb")+c.suffix;api.Check(api.hipModuleGetFunction(&f,m,name.c_str()),"function");
  int blocks=0;api.Check(occupancy(&blocks,f,c.threads,0),"occupancy");
  printf("case=%s threads=%d active_blocks_per_MP=%d resident_threads_bound=%d resident_waves_bound=%d\n",c.dir,c.threads,blocks,blocks*c.threads,blocks*c.threads/p.warpSize);
  api.Check(api.hipModuleUnload(m),"unload");
 }
 return 0;
}catch(const std::exception&e){fprintf(stderr,"FAIL %s\n",e.what());return 1;}}
