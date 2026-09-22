#include "hip_api.h"
int main(int argc,char**argv){try{
 if(argc!=2&&argc!=3)throw std::runtime_error("usage: occupancy.exe MODULE");hip_probe::Api api;api.Check(api.hipInit(0),"init");api.Check(api.hipSetDevice(0),"device");auto p=api.Properties(0);
 printf("warp=%d MPs=%d maxThreadsPerMP=%d sharedPerMP=%zu\n",p.warpSize,p.multiProcessorCount,p.maxThreadsPerMultiProcessor,p.sharedMemPerMultiprocessor);
 using Fn=int(*)(int*,void*,int,size_t);Fn query{};api.Load(query,"hipModuleOccupancyMaxActiveBlocksPerMultiprocessor");void*m{};api.Check(api.LoadModule(&m,argv[1]),"module");
 for(const char*n:{"vit_expand_blocked_fp8_frag_bytein","probe_control","probe_m32n32_u4","probe_m32n32_u1","probe_m32n32_col"}){
  void*f{};api.Check(api.hipModuleGetFunction(&f,m,n),"function");int threads=std::string(n)=="probe_group4"?128:std::string(n)=="probe_group8"?256:32,blocks{};api.Check(query(&blocks,f,threads,0),"occupancy");printf("kernel=%s threads=%d blocks_per_MP=%d waves_bound=%d\n",n,threads,blocks,blocks*threads/32);
 }
 if(argc==3)for(const char*n:{"probe_tiled_balanced","probe_tiled_m16"}){void*f{};api.Check(api.hipModuleGetFunction(&f,m,n),"function");int blocks{};api.Check(query(&blocks,f,32,0),"occupancy");printf("kernel=%s threads=32 blocks_per_MP=%d waves_bound=%d\n",n,blocks,blocks);}
 api.Check(api.hipModuleUnload(m),"unload");return 0;
}catch(const std::exception&e){fprintf(stderr,"FAIL %s\n",e.what());return 1;}}
