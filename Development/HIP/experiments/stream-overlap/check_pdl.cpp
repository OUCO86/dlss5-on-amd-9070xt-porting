// Chain of K `stage` launches (pdl.hip) on one stream: normal launches (barrier bit) versus hipExtAnyOrderLaunch with
// in-kernel flag waits. Verifies the final data against a CPU model (so the acquire/release path really made the
// producer's data visible) and reports per-launch wall time for both, plus the poll counts.
#include "../../hip_api.h"
#include <chrono>
#include <vector>
#include <algorithm>
#include <functional>
using namespace hip_probe;
static double Median(std::vector<double>v){std::sort(v.begin(),v.end());return v[v.size()/2];}
int main(int argc,char**argv){try{
 if(argc!=2)throw std::runtime_error("check_pdl PDL_MODULE");
 Api a(7);a.Check(a.hipInit(0),"init");a.Check(a.hipSetDevice(0),"device");
 int(*hipExtModuleLaunchKernel)(Handle,unsigned,unsigned,unsigned,unsigned,unsigned,unsigned,size_t,Handle,void**,void**,Handle,Handle,unsigned){};a.Load(hipExtModuleLaunchKernel,"hipExtModuleLaunchKernel");
 Handle s{},module{},fn{};a.Check(a.hipStreamCreate(&s),"stream");a.Check(a.hipModuleLoad(&module,argv[1]),"module");a.Check(a.hipModuleGetFunction(&fn,module,"stage"),"function");
 const unsigned K=32,GMAX=512,FSTRIDE_MAX=64;unsigned*flags{},*data{},*waits{};
 a.Check(a.hipMalloc((void**)&flags,size_t(K)*GMAX*FSTRIDE_MAX*4),"flags");a.Check(a.hipMalloc((void**)&data,size_t(K)*GMAX*4),"data");a.Check(a.hipMalloc((void**)&waits,size_t(K)*GMAX*4),"waits");
 a.Check(a.hipMemsetAsync(flags,0,size_t(K)*GMAX*FSTRIDE_MAX*4,s),"zero");a.Check(a.hipStreamSynchronize(s),"zero sync");
 unsigned epoch=0;
 unsigned stride=1,sleep=1;
 auto chain=[&](unsigned cycles,unsigned groups,bool anyorder,bool record){++epoch;
  for(unsigned k=0;k<K;k++){unsigned*fi=k?flags+size_t(k-1)*GMAX*stride:nullptr,*fo=flags+size_t(k)*GMAX*stride,*di=k?data+(k-1)*GMAX:data,*dout=data+k*GMAX,*w=record?waits+k*GMAX:nullptr;
   void*args[]={&cycles,&fi,&fo,&di,&dout,&epoch,&groups,&w,&stride,&sleep};
   if(anyorder)a.Check(hipExtModuleLaunchKernel(fn,groups*256,1,1,256,1,1,0,s,args,nullptr,nullptr,nullptr,1),"ext launch");
   else a.Check(a.hipModuleLaunchKernel(fn,groups,1,1,256,1,1,0,s,args,nullptr),"launch");}};
 auto time=[&](const std::function<void()>&body,int trials=7){std::vector<double>w;for(int t=0;t<trials;t++){a.Check(a.hipStreamSynchronize(s),"pre");auto t0=std::chrono::steady_clock::now();body();a.Check(a.hipStreamSynchronize(s),"post");w.push_back(std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-t0).count());}return Median(w);};
 auto verify=[&](unsigned groups){std::vector<unsigned>d(size_t(K)*GMAX),w(size_t(K)*GMAX);a.Check(a.hipMemcpy(d.data(),data,d.size()*4,2),"read data");a.Check(a.hipMemcpy(w.data(),waits,w.size()*4,2),"read waits");
  std::vector<unsigned>m(size_t(K)*GMAX);for(unsigned k=0;k<K;k++)for(unsigned g=0;g<groups;g++){unsigned g1=g+1<groups?g+1:g;unsigned x=k?m[(k-1)*GMAX+g]:0,y=k?m[(k-1)*GMAX+g1]:0;m[k*GMAX+g]=x*3u+y+g+epoch;}
  size_t bad=0;for(unsigned k=0;k<K;k++)for(unsigned g=0;g<groups;g++)if(d[k*GMAX+g]!=m[k*GMAX+g])bad++;
  unsigned long long polls=0,maxp=0;for(unsigned k=1;k<K;k++)for(unsigned g=0;g<groups;g++){polls+=w[k*GMAX+g];maxp=std::max<unsigned long long>(maxp,w[k*GMAX+g]);}
  return std::make_tuple(bad,double(polls)/((K-1)*groups),maxp);};
 chain(1000,64,true,false);chain(1000,64,false,false);a.Check(a.hipStreamSynchronize(s),"warm");
 for(auto cfg:{std::make_pair(1u,1u),std::make_pair(1u,8u),std::make_pair(64u,1u),std::make_pair(64u,8u)}){stride=cfg.first;sleep=cfg.second;printf("== flag stride %u words, poll sleep %u ==\n",stride,sleep);
 for(unsigned cycles:{50000u,400000u})for(unsigned groups:{64u,128u,200u,300u}){
  double serial=time([&]{chain(cycles,groups,false,false);});
  double any=time([&]{chain(cycles,groups,true,true);});
  auto[bad,avgp,maxp]=verify(groups);
  printf("cycles=%u groups=%u (waves/SIMD %.1f of 16): per-launch us serial=%.1f anyorder+flags=%.1f (%.0f%%)  mismatches=%zu avg_polls=%.1f max_polls=%llu\n",cycles,groups,groups*8/128.0,serial*1000/K,any*1000/K,100*any/serial,bad,avgp,maxp);}}
 a.hipFree(flags);a.hipFree(data);a.hipFree(waits);a.hipModuleUnload(module);a.hipStreamDestroy(s);return 0;
}catch(const std::exception&e){fprintf(stderr,"%s\n",e.what());return 2;}}
