#include "../../hip_api.h"
using namespace hip_probe;
int main(int argc,char**argv){try{if(argc!=2)return 2;Api a;a.Check(a.hipInit(0),"init");a.Check(a.hipSetDevice(0),"device");using Occ=int(*)(int*,Handle,int,size_t);using Attr=int(*)(int*,int,Handle);Occ occ{};Attr attr{};a.Load(occ,"hipModuleOccupancyMaxActiveBlocksPerMultiprocessor");a.Load(attr,"hipFuncGetAttribute");Handle m{};a.Check(a.LoadModule(&m,argv[1]),"module");
for(const char*kind:{"mat","load"})for(unsigned W:{1u,2u,4u,8u})for(unsigned p=0;p<(W==1?1u:2u);p++){std::string n=std::string(kind)+"_"+(p?"m":"i")+std::to_string(W);Handle f{};a.Check(a.hipModuleGetFunction(&f,m,n.c_str()),"fn");int regs{},blocks{};a.Check(attr(&regs,4,f),"regs");a.Check(occ(&blocks,f,W*32,0),"occupancy");printf("name=%s threads=%u regs=%d groups_per_MP=%d waves_bound=%u\n",n.c_str(),W*32,regs,blocks,blocks*W);}
a.hipModuleUnload(m);return 0;}catch(const std::exception&e){fprintf(stderr,"FAIL %s\n",e.what());return 1;}}
