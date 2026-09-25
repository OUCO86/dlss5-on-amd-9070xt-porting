// Can a second stream fill a launch's tail on this driver, and what does the cross-stream dependency cost?
// Four measurements, all wall clock (steady_clock, first enqueue -> completion), median of 7:
//  A  launch gap: N back-to-back spin(0) launches on one stream, per-launch floor (same as check_launch_gap).
//  B  event ping-pong: streams S0/S1, each step = launch spin(0) on S0, record e0 (no timing), S1 waits e0,
//     launch on S1, record e1, S0 waits e1. Per-step cost minus two launch gaps = what one pair of
//     record+wait costs. This is the price the two-stream schedule pays per block boundary.
//  C  overlap: spin(T) with G groups (G*8 waves, well under the 128 SIMD x 16 slots), launched twice:
//     same stream (expect 2T), two streams (T if they really run concurrently), and same stream with
//     hipExtModuleLaunchKernel flags=hipExtAnyOrderLaunch (T if the barrier bit is really dropped).
//  D  staggered chain: K steps, each step = big spin on S0 + big spin on S1 with a cross dependency
//     (S1 step k waits S0 step k, S0 step k+1 waits S1 step k): the two-stream pipeline pattern.
//     Compare with 2K launches on one stream.
#include "../../hip_api.h"
#include <chrono>
#include <vector>
#include <algorithm>
#include <functional>
using namespace hip_probe;
static double Median(std::vector<double>v){std::sort(v.begin(),v.end());return v[v.size()/2];}
int main(int argc,char**argv){try{
 if(argc!=2)throw std::runtime_error("check_stream_overlap SPIN_MODULE");
 Api a(7);a.Check(a.hipInit(0),"init");a.Check(a.hipSetDevice(0),"device");int version=0;a.Check(a.hipRuntimeGetVersion(&version),"version");printf("runtime=%d\n",version);
 int(*hipEventCreateWithFlags)(Handle*,unsigned){};int(*hipStreamWaitEvent)(Handle,Handle,unsigned){};
 int(*hipExtModuleLaunchKernel)(Handle,unsigned,unsigned,unsigned,unsigned,unsigned,unsigned,size_t,Handle,void**,void**,Handle,Handle,unsigned){};
 a.Load(hipEventCreateWithFlags,"hipEventCreateWithFlags");a.Load(hipStreamWaitEvent,"hipStreamWaitEvent");
 bool ext=true;try{a.Load(hipExtModuleLaunchKernel,"hipExtModuleLaunchKernel");}catch(...){ext=false;printf("hipExtModuleLaunchKernel: missing\n");}
 Handle s0{},s1{},module{},fn{};a.Check(a.hipStreamCreate(&s0),"stream0");a.Check(a.hipStreamCreate(&s1),"stream1");
 a.Check(a.hipModuleLoad(&module,argv[1]),"module");a.Check(a.hipModuleGetFunction(&fn,module,"spin"),"function");
 unsigned*out{};a.Check(a.hipMalloc((void**)&out,4096*4),"out");
 auto launch=[&](Handle s,unsigned ticks,unsigned groups,unsigned flags=0){void*args[]={&ticks,&out};
  if(flags){if(!ext)throw std::runtime_error("ext launch unavailable");a.Check(hipExtModuleLaunchKernel(fn,groups*256,1,1,256,1,1,0,s,args,nullptr,nullptr,nullptr,flags),"ext launch");}
  else a.Check(a.hipModuleLaunchKernel(fn,groups,1,1,256,1,1,0,s,args,nullptr),"launch");};
 auto sync=[&]{a.Check(a.hipStreamSynchronize(s0),"sync0");a.Check(a.hipStreamSynchronize(s1),"sync1");};
 auto time=[&](const std::function<void()>&body,int trials=7){std::vector<double>w;for(int t=0;t<trials;t++){sync();auto t0=std::chrono::steady_clock::now();body();sync();w.push_back(std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-t0).count());}return Median(w);};
 for(int i=0;i<50;i++){launch(s0,0,1);launch(s1,0,1);}sync();
 // A
 for(unsigned n:{64u,256u,1024u}){double ms=time([&]{for(unsigned i=0;i<n;i++)launch(s0,0,1);});printf("A launch_gap n=%u wall_ms=%.4f per_launch_us=%.2f\n",n,ms,ms*1000/n);}
 // B
 std::vector<Handle>ev(2048);for(auto&e:ev)a.Check(hipEventCreateWithFlags(&e,2/*hipEventDisableTiming*/),"event");
 for(unsigned n:{64u,256u,1024u}){
  double ms=time([&]{for(unsigned i=0;i<n;i++){launch(s0,0,1);a.Check(a.hipEventRecord(ev[2*i%2048],s0),"rec0");a.Check(hipStreamWaitEvent(s1,ev[2*i%2048],0),"wait1");launch(s1,0,1);a.Check(a.hipEventRecord(ev[(2*i+1)%2048],s1),"rec1");a.Check(hipStreamWaitEvent(s0,ev[(2*i+1)%2048],0),"wait0");}});
  double one=time([&]{for(unsigned i=0;i<2*n;i++)launch(s0,0,1);});
  printf("B pingpong n=%u wall_ms=%.4f per_step_us=%.2f  vs 2n launches one stream per_step_us=%.2f  -> record+wait pair ~%.2f us\n",n,ms,ms*1000/n,one*1000/n,(ms-one)*1000/n);}
 // sync floor
 printf("sync floor (no work) = %.3f ms\n",time([&]{}));
 // C/D long chains: K launches of spin(T). Per-launch = (wall - floor)/K.
 const unsigned T=400000; // SHADER_CYCLES ~2.5 GHz: ~160 us per wave
 double floor_=time([&]{});
 for(unsigned g:{32u,64u,128u}){const unsigned K=32;
  double serial=time([&]{for(unsigned i=0;i<K;i++)launch(s0,T,g);});
  double two=time([&]{for(unsigned i=0;i<K;i++)launch(i&1?s1:s0,T,g);});
  double any=ext?time([&]{for(unsigned i=0;i<K;i++)launch(s0,T,g,1/*hipExtAnyOrderLaunch*/);}):-1;
  double chain=time([&]{for(unsigned i=0;i<K/2;i++){launch(s0,T,g);a.Check(a.hipEventRecord(ev[2*i%2048],s0),"rec0");a.Check(hipStreamWaitEvent(s1,ev[2*i%2048],0),"wait1");launch(s1,T,g);a.Check(a.hipEventRecord(ev[(2*i+1)%2048],s1),"rec1");a.Check(hipStreamWaitEvent(s0,ev[(2*i+1)%2048],0),"wait0");}});
  printf("chain K=%u groups=%u (waves/SIMD=%.1f): per-launch us  serial_one_stream=%.1f  two_streams_independent=%.1f  any_order_one_stream=%.1f  two_streams_event_chain=%.1f\n",K,g,g*8/128.0,(serial-floor_)*1000/K,(two-floor_)*1000/K,any<0?-1:(any-floor_)*1000/K,(chain-floor_)*1000/K);}
 std::vector<unsigned>counts(4096);a.Check(a.hipMemcpy(counts.data(),out,4096*4,2),"read");printf("spin poll count sample=%u\n",counts[0]);
 for(auto&e:ev)a.hipEventDestroy(e);a.hipFree(out);a.hipModuleUnload(module);a.hipStreamDestroy(s0);a.hipStreamDestroy(s1);return 0;
}catch(const std::exception&e){fprintf(stderr,"%s\n",e.what());return 2;}}
