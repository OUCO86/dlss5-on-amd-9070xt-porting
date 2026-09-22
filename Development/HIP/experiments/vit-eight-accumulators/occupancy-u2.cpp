#include "hip_api.h"
int main(int argc,char**argv){try{
 if(argc!=2)throw std::runtime_error("usage: occupancy.exe MODULE");hip_probe::Api api;api.Check(api.hipInit(0),"init");api.Check(api.hipSetDevice(0),"device");auto p=api.Properties(0);
 printf("warp=%d MPs=%d maxThreadsPerMP=%d sharedPerMP=%zu\n",p.warpSize,p.multiProcessorCount,p.maxThreadsPerMultiProcessor,p.sharedMemPerMultiprocessor);
 using Fn=int(*)(int*,void*,int,size_t);Fn query{};api.Load(query,"hipModuleOccupancyMaxActiveBlocksPerMultiprocessor");using Attr=int(*)(int*,int,void*);Attr attr{};api.Load(attr,"hipFuncGetAttribute");void*m{};api.Check(api.LoadModule(&m,argv[1]),"module");
 for(const char*n:{"vit_expand_blocked_fp8_frag_bytein","probe_m16n128_row","probe_m32n64_row","probe_m16n128_tile","probe_m32n64_tile","probe_m16n128_row_u2","probe_m32n64_row_u2","probe_m16n128_tile_u2","probe_m32n64_tile_u2"}){
  void*f{};api.Check(api.hipModuleGetFunction(&f,m,n),"function");int threads=std::string(n)=="probe_group4"?128:std::string(n)=="probe_group8"?256:32,blocks{};api.Check(query(&blocks,f,threads,0),"occupancy");int regs=0;api.Check(attr(&regs,4,f),"NUM_REGS");printf("runtime_num_regs=%d ",regs);printf("kernel=%s threads=%d blocks_per_MP=%d waves_bound=%d\n",n,threads,blocks,blocks*threads/32);
 }api.Check(api.hipModuleUnload(m),"unload");return 0;
}catch(const std::exception&e){fprintf(stderr,"FAIL %s\n",e.what());return 1;}}
