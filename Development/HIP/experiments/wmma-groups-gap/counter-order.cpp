#include "../../hip_api.h"
#include <vector>
#include <chrono>
#include <cmath>
using namespace hip_probe;
int main(int argc,char**argv){try{
 if(argc!=3)throw std::runtime_error("module stride");unsigned stride=std::stoul(argv[2]);if(stride!=1&&stride!=129)throw std::runtime_error("stride");std::string target="order_mat";unsigned span=1024,pitch=16384,W=1;

 Api a;a.Check(a.hipInit(0),"init");a.Check(a.hipSetDevice(0),"device");Handle m{},f{},s{};a.Check(a.LoadModule(&m,argv[1]),"module");a.Check(a.hipModuleGetFunction(&f,m,target.c_str()),"kernel");a.Check(a.hipStreamCreate(&s),"stream");
 std::vector<unsigned char>av(640*1024,0x18),bv(4096*1024,0x18);void*A{},*B{},*out{};a.Check(a.hipMalloc(&A,av.size()),"A");a.Check(a.hipMalloc(&B,bv.size()),"B");a.Check(a.hipMalloc(&out,2560*32*4),"out");a.Check(a.hipMemcpy(A,av.data(),av.size(),1),"upload A");a.Check(a.hipMemcpy(B,bv.data(),bv.size(),1),"upload B");
 unsigned am=stride,bm=span-1,rounds=16;void*args[]={&A,&B,&out,&am,&bm,&rounds,&pitch};
 auto launch=[&](){a.Check(a.hipModuleLaunchKernel(f,2560/W,1,1,W*32,1,1,0,s,args,nullptr),"launch");};
 auto check=[&](){a.Check(a.hipStreamSynchronize(s),"sync");std::vector<float>x(2560*32);a.Check(a.hipMemcpy(x.data(),out,x.size()*4,2),"read");size_t bad=0;for(float v:x)bad+=v!=208.f||!std::isfinite(v);printf("CHECK kernel=%s bad=%llu\n",target.c_str(),(unsigned long long)bad);fflush(stdout);if(bad)throw std::runtime_error("output mismatch");};
 launch();check();printf("TARGET %s stride=%u\n",target.c_str(),stride);fflush(stdout);
 for(unsigned i=0;i<10000;i++)launch();check();
 // Keep the pure-HIP process alive/dispatching while RDP finishes writing the trace.
 auto t=std::chrono::steady_clock::now();while(std::chrono::duration<double>(std::chrono::steady_clock::now()-t).count()<15.){for(unsigned i=0;i<256;i++)launch();a.Check(a.hipStreamSynchronize(s),"tail");}
 check();a.hipFree(A);a.hipFree(B);a.hipFree(out);a.hipStreamDestroy(s);a.hipModuleUnload(m);return 0;
}catch(const std::exception&e){fprintf(stderr,"FAIL %s\n",e.what());return 1;}}
