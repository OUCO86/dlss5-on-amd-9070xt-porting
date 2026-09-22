#include "../../hip_api.h"
using namespace hip_probe;
int main(int argc,char**argv){try{
 if(argc!=2)return 2;Api a;a.Check(a.hipInit(0),"init");a.Check(a.hipSetDevice(0),"device");
 using Occ=int(*)(int*,Handle,int,size_t);using Attr=int(*)(int*,int,Handle);Occ occ{};Attr attr{};a.Load(occ,"hipModuleOccupancyMaxActiveBlocksPerMultiprocessor");a.Load(attr,"hipFuncGetAttribute");Handle m{};a.Check(a.LoadModule(&m,argv[1]),"module");
 for(const char*n:{"masked4","pitched4"}){Handle f{};a.Check(a.hipModuleGetFunction(&f,m,n),"fn");int regs{},blocks{};a.Check(attr(&regs,4,f),"regs");a.Check(occ(&blocks,f,32,0),"occupancy");printf("name=%s runtime_regs=%d blocks_per_MP=%d waves_bound=%d\n",n,regs,blocks,blocks);}
 a.hipModuleUnload(m);return 0;
}catch(const std::exception&e){fprintf(stderr,"FAIL %s\n",e.what());return 1;}}
