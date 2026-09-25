#pragma once
#include <unordered_map>
#include <memory>
#include <cstddef>
#include <cmath>
#include <deque>
#include <atomic>

// EXPERIMENT ONLY: the captured list must contain no consumers of the FFX output
// after the dispatch site. This is the Stellar Blade submission contract, not a
// general command-list splitter. Never close/reset a game-owned command list.
namespace NativePreUpscale {
struct Description {
 Header header;void*command_list;ResourcePayload resources[7];
 float jitter[2],motion_scale[2];uint32_t render[2],upscale[2];
 bool sharpen;char pad0[3];float sharpness,frame_time,pre_exposure;
 bool reset;char pad1[3];float near_plane,far_plane,fov,meters;uint32_t flags;
};
static_assert(sizeof(Description)==432,"FFX dispatch ABI");
static_assert(offsetof(Description,jitter)==360&&offsetof(Description,motion_scale)==368&&offsetof(Description,render)==376&&offsetof(Description,upscale)==384&&offsetof(Description,flags)==428,"FFX dispatch offsets");
inline int Mode(){
 const wchar_t*v=_wgetenv(L"DLSS5_PRE_UPSCALE");if(v)return !wcscmp(v,L"1")?1:!wcscmp(v,L"2")?2:0;
 static int configured=[](){int mode=0;if(FILE*f=_wfopen(NativeLabPath(L"native-game-flags.txt").c_str(),L"rb")){char line[256];while(fgets(line,sizeof line,f)){size_t n=strlen(line);while(n&&(line[n-1]=='\n'||line[n-1]=='\r'||line[n-1]==' '))line[--n]=0;if(!strcmp(line,"DLSS5_PRE_UPSCALE=1"))mode=1;else if(!strcmp(line,"DLSS5_PRE_UPSCALE=2"))mode=2;else if(!strcmp(line,"DLSS5_PRE_UPSCALE=0"))mode=0;}fclose(f);}return mode;}();return configured;
}
inline bool Enabled(){return Mode()!=0;}
inline bool FitLargeFromFile(){static const bool v=[]{unsigned x=0;if(FILE*f=_wfopen(NativeLabPath(L"native-game-flags.txt").c_str(),L"rb")){char line[256];while(fgets(line,sizeof line,f))sscanf(line,"DLSS5_FIT_LARGE=%u",&x);fclose(f);}return x==1;}();return v;}
struct DisplaySettings {unsigned notice=2;unsigned fps=0;};
inline const DisplaySettings&Display(){
 // Read before the background initializer applies flags to the environment.
 static const DisplaySettings settings=[](){DisplaySettings v;
  if(FILE*f=_wfopen(NativeLabPath(L"native-game-flags.txt").c_str(),L"rb")){
   char line[256];while(fgets(line,sizeof line,f)){unsigned n;
    if(sscanf(line,"DLSS5_NOTICE=%u",&n)==1)v.notice=n;
    if(sscanf(line,"DLSS5_SHOW_FPS=%u",&n)==1)v.fps=n;
   }fclose(f);
  }return v;
 }();return settings;
}

inline bool Async(){
 /* DLSS5_PRE_UPSCALE_ASYNC = 1 | 0 | auto. auto (the shipped template since 0.30): per-title quirk table -- engines whose FSR colour
    buffer is a transient aliased resource must submit synchronously, otherwise the deferred copy reads whatever the memory holds at
    that moment (Cyberpunk 2077 2.31: a sky probe; picture only changed in tone). Everything else keeps the asynchronous submission. */
 static const int mode=[](){
  auto parse=[](const wchar_t*v)->int{if(!v)return -1;if(!wcscmp(v,L"1"))return 1;if(!wcscmp(v,L"0"))return 0;return -1;};
  int m=parse(_wgetenv(L"DLSS5_PRE_UPSCALE_ASYNC"));
  if(m<0){char v[16]{};if(FILE*f=_wfopen(NativeLabPath(L"native-game-flags.txt").c_str(),L"rb")){char line[256];while(fgets(line,sizeof line,f))sscanf(line,"DLSS5_PRE_UPSCALE_ASYNC=%15s",v);fclose(f);}
   if(!strcmp(v,"1"))m=1;else if(!strcmp(v,"0"))m=0;}
  if(m<0){wchar_t exe[MAX_PATH]{};GetModuleFileNameW(nullptr,exe,MAX_PATH);const wchar_t*base=wcsrchr(exe,L'\\');base=base?base+1:exe;
   static const wchar_t*const sync_titles[]={L"Cyberpunk2077.exe"};m=1;for(const wchar_t*t:sync_titles)if(!_wcsicmp(base,t))m=0;
   if(FILE*f=_wfopen(NativeLabPath(L"logs\\native-pre-upscale.txt").c_str(),L"ab")){fprintf(f,"async=auto exe=%ls -> %s\n",base,m?"asynchronous":"synchronous (quirk)");fclose(f);}}
  return m;}();
 return mode==1;
}
inline LONG CALLBACK ExceptionTrace(EXCEPTION_POINTERS*p){
 if(!p||p->ExceptionRecord->ExceptionCode!=EXCEPTION_ACCESS_VIOLATION)return EXCEPTION_CONTINUE_SEARCH;
 static std::atomic<unsigned>count{};if(count.fetch_add(1)>3)return EXCEPTION_CONTINUE_SEARCH;
 if(FILE*f=_wfopen(NativeLabPath(L"logs\\native-pre-exception.txt").c_str(),L"ab")){
  fprintf(f,"pid=%lu code=%08lx ip=%p access=%llu address=%llx rcx=%llx rdx=%llx r8=%llx r9=%llx\n",GetCurrentProcessId(),p->ExceptionRecord->ExceptionCode,p->ExceptionRecord->ExceptionAddress,(unsigned long long)p->ExceptionRecord->ExceptionInformation[0],(unsigned long long)p->ExceptionRecord->ExceptionInformation[1],(unsigned long long)p->ContextRecord->Rcx,(unsigned long long)p->ContextRecord->Rdx,(unsigned long long)p->ContextRecord->R8,(unsigned long long)p->ContextRecord->R9);
  void*stack[32]{};USHORT n=CaptureStackBackTrace(0,32,stack,nullptr);for(USHORT i=0;i<n;i++){HMODULE m=nullptr;wchar_t path[MAX_PATH]{};GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,reinterpret_cast<LPCWSTR>(stack[i]),&m);if(m)GetModuleFileNameW(m,path,MAX_PATH);fprintf(f,"  %p %ls+%llx\n",stack[i],path,(unsigned long long)(reinterpret_cast<uintptr_t>(stack[i])-reinterpret_cast<uintptr_t>(m)));}fclose(f);
 }return EXCEPTION_CONTINUE_SEARCH;
}
inline void InstallExceptionTrace(){if(Enabled()){static auto h=AddVectoredExceptionHandler(1,ExceptionTrace);(void)h;}}
inline std::atomic<bool>&Fatal(){static std::atomic<bool>fatal{false};return fatal;}
inline bool&ReplayFlag(){static thread_local bool v=false;return v;}
inline bool Replaying(){return ReplayFlag();}
inline ID3D12Resource*&PrivateBarrierResource(){static thread_local ID3D12Resource*r=nullptr;return r;}
inline D3D12_RESOURCE_STATES&PrivateBarrierState(){static thread_local D3D12_RESOURCE_STATES s=D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE;return s;}
template<class BarrierFunction>inline bool FixPrivateBarriers(ID3D12GraphicsCommandList*c,UINT count,const D3D12_RESOURCE_BARRIER*b,BarrierFunction call){
 if(!PrivateBarrierResource()||!b)return false;
 std::vector<D3D12_RESOURCE_BARRIER>fixed;fixed.reserve(count);
 for(UINT i=0;i<count;i++){auto v=b[i];
  if(v.Type==D3D12_RESOURCE_BARRIER_TYPE_TRANSITION&&v.Transition.pResource==PrivateBarrierResource()&&v.Flags==D3D12_RESOURCE_BARRIER_FLAG_NONE){
   /* OptiScaler applies its engine-specific RT->SRV barrier even for our private SRV input.
      Only our own texture is rebased; game-owned resource barriers are never rewritten. */
   v.Transition.StateBefore=PrivateBarrierState();PrivateBarrierState()=v.Transition.StateAfter;
   if(v.Transition.StateBefore==v.Transition.StateAfter)continue;
  }fixed.push_back(v);
 }
 if(!fixed.empty())call(c,UINT(fixed.size()),fixed.data());return true;
}
struct Guard{bool old;Guard():old(ReplayFlag()){ReplayFlag()=true;}~Guard(){ReplayFlag()=old;}};
struct Job{
 Description desc{};void*context{};ID3D12GraphicsCommandList*list{};ID3D12Device*record_device{};unsigned frame{};
 D3D12_RESOURCE_STATES states[7]{};bool uncertain{};unsigned following_work{};
 ~Job(){for(auto&r:desc.resources)if(r.resource)static_cast<ID3D12Resource*>(r.resource)->Release();if(list)list->Release();if(record_device)record_device->Release();}
};
inline std::mutex&Mutex(){static std::mutex m;return m;}
inline auto&Jobs(){static std::unordered_map<ID3D12GraphicsCommandList*,std::unique_ptr<Job>>jobs;return jobs;}
// Published under Mutex: idle game draws must not contend on the job map.
inline std::atomic<bool>&PendingJobs(){static std::atomic<bool>pending{false};return pending;}
inline bool HasPendingJobs(){return PendingJobs().load(std::memory_order_acquire);}
inline void Log(unsigned frame,const Description&d,const char*event,bool processed=false,uint32_t result=0){
 if(FILE*f=_wfopen(NativeLabPath(L"logs\\native-pre-upscale.txt").c_str(),L"ab")){fprintf(f,"frame=%u render=%ux%u upscale=%ux%u phase=%u processed=%u replay=%u history_reset=1 event=%s\n",frame,d.render[0],d.render[1],d.upscale[0]?d.upscale[0]:d.resources[6].width,d.upscale[1]?d.upscale[1]:d.resources[6].height,neural_oneshot.Phase(),processed,result,event);fclose(f);}
}
inline bool Read(const void*src,void*dst,size_t n){SIZE_T got=0;return src&&ReadProcessMemory(GetCurrentProcess(),src,dst,n,&got)&&got==n;}
inline bool Reverse(D3D12_RESOURCE_STATES s,uint32_t&out){
 switch(s){case D3D12_RESOURCE_STATE_COMMON:out=1;return true;case D3D12_RESOURCE_STATE_UNORDERED_ACCESS:out=2;return true;
 case D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE:out=4;return true;case D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE:out=8;return true;
 case (int(D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE)|int(D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE)):out=12;return true;
 case D3D12_RESOURCE_STATE_COPY_SOURCE:out=16;return true;case D3D12_RESOURCE_STATE_COPY_DEST:out=32;return true;
 case D3D12_RESOURCE_STATE_GENERIC_READ:out=20;return true;case D3D12_RESOURCE_STATE_RENDER_TARGET:out=256;return true;
 case D3D12_RESOURCE_STATE_DEPTH_WRITE:out=512;return true;case D3D12_RESOURCE_STATE_DEPTH_READ:out=512;return true; /* PRESENT == COMMON (0) in D3D12 */
 /* 2026-09-24 (Cyberpunk 2077): the game leaves FSR inputs in read-combination states after the upscaler. Any pure read combination of
    shader/copy/depth-read bits maps to the FFX read state that covers it (the FFX side only distinguishes compute/pixel/copy reads); a
    DEPTH_READ|shader-read combination is still shader-readable. Same rule as the forward map: mask off the bits FFX cannot express. */
 default:{const D3D12_RESOURCE_STATES read=D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE|D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE|D3D12_RESOURCE_STATE_COPY_SOURCE|D3D12_RESOURCE_STATE_DEPTH_READ|D3D12_RESOURCE_STATE_VERTEX_AND_CONSTANT_BUFFER|D3D12_RESOURCE_STATE_INDEX_BUFFER|D3D12_RESOURCE_STATE_INDIRECT_ARGUMENT;
  if(s==0||(s&~read))return false;out=0;if(s&D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE)out|=4;if(s&D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE)out|=8;if(s&D3D12_RESOURCE_STATE_COPY_SOURCE)out|=16;if(!out)out=4;return true;}}
}
inline bool Capture(void**context,const Header*h,ID3D12GraphicsCommandList*native,unsigned frame){
 if(Fatal().load()||!Enabled()||Replaying()||!original||!native||native->GetType()!=D3D12_COMMAND_LIST_TYPE_DIRECT)return false;
 // Return false so the caller records the original FFX dispatch in its own list.
 if(Mode()==1&&neural_oneshot.Bypassed())return false;
 Description d{};void*ctx=nullptr;
 if(!Read(h,&d,sizeof d)||!Read(context,&ctx,sizeof ctx)||!ctx||!d.command_list){if(frame<=8)Log(frame,d,"capture rejected: descriptor/context read");return false;}
 if(d.header.next){if(frame<=8)Log(frame,d,"capture rejected: extension chain");return false;}
 /* upscaleSize=0 is legal and used by Stellar Blade: FFX uses the context's maxUpscaleSize. */
 if(!d.resources[0].resource||!d.resources[1].resource||!d.resources[2].resource||!d.resources[6].resource||!d.render[0]||!d.render[1])return false;
 for(unsigned i=0;i<6;i++)if(d.resources[i].resource==d.resources[6].resource)return false; // in-place upscaling is unsupported
 for(float x:d.jitter)if(!std::isfinite(x))return false;for(float x:d.motion_scale)if(!std::isfinite(x))return false;
 if(frame<=8)Log(frame,d,"capture descriptor read");
 D3D12_RESOURCE_STATES states[7]{};
 for(unsigned i=0;i<7;i++)if(d.resources[i].resource){if(!ffx_state_to_d3d12(d.resources[i].state,states[i]))return false;
  auto r=static_cast<ID3D12Resource*>(d.resources[i].resource)->GetDesc();
  if(r.Dimension!=D3D12_RESOURCE_DIMENSION_TEXTURE2D||r.SampleDesc.Count!=1||r.DepthOrArraySize!=1||r.MipLevels!=1)return false;
  if(!d.resources[i].width||!d.resources[i].height||d.resources[i].width>r.Width||d.resources[i].height>r.Height)return false;
  if(i==0&&(d.render[0]>r.Width||d.render[1]>r.Height))return false;
  if(i==6&&(d.upscale[0]>r.Width||d.upscale[1]>r.Height))return false;
  for(unsigned k=0;k<i;k++)if(d.resources[k].resource==d.resources[i].resource&&states[k]!=states[i])return false;
 }
 std::lock_guard<std::mutex>lock(Mutex());if(Jobs().count(native))return false;
 auto j=std::make_unique<Job>();j->desc=d;j->context=ctx;j->list=native;j->frame=frame;native->AddRef();
 for(unsigned i=0;i<7;i++){j->states[i]=states[i];if(d.resources[i].resource)static_cast<ID3D12Resource*>(d.resources[i].resource)->AddRef();}
 if(FAILED(static_cast<ID3D12GraphicsCommandList*>(d.command_list)->GetDevice(IID_PPV_ARGS(&j->record_device))))return false;
 Jobs().emplace(native,std::move(j));PendingJobs().store(true,std::memory_order_release);if(frame<5)Log(frame,d,"captured: experimental no-following-consumer contract");return true;
}
inline void ObserveBarrier(ID3D12GraphicsCommandList*list,UINT count,const D3D12_RESOURCE_BARRIER*b){
 if(!HasPendingJobs()||Replaying()||!b)return;std::lock_guard<std::mutex>lock(Mutex());auto it=Jobs().find(list);if(it==Jobs().end())return;auto&j=*it->second;
 for(UINT n=0;n<count;n++){auto&v=b[n];if(v.Type!=D3D12_RESOURCE_BARRIER_TYPE_TRANSITION)continue;
  for(unsigned i=0;i<7;i++)if(j.desc.resources[i].resource==v.Transition.pResource){
   if(v.Flags==D3D12_RESOURCE_BARRIER_FLAG_BEGIN_ONLY){j.uncertain=true;continue;}
   if(v.Transition.Subresource!=D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES&&v.Transition.Subresource!=0){j.uncertain=true;continue;}
   j.states[i]=v.Transition.StateAfter;
  }
 }
}
inline void ObserveWork(ID3D12GraphicsCommandList*list){
 if(!HasPendingJobs()||Replaying())return;std::lock_guard<std::mutex>lock(Mutex());auto it=Jobs().find(list);if(it!=Jobs().end())++it->second->following_work;
}
inline void Transition(ID3D12GraphicsCommandList*c,ID3D12Resource*r,D3D12_RESOURCE_STATES a,D3D12_RESOURCE_STATES b){if(!r||a==b)return;D3D12_RESOURCE_BARRIER v{};v.Type=D3D12_RESOURCE_BARRIER_TYPE_TRANSITION;v.Transition={r,D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES,a,b};c->ResourceBarrier(1,&v);}
struct Runtime{NativeGameSubmission submit;NativeTextOverlay overlay;ID3D12Resource*low{};bool failed{};
 std::deque<std::pair<UINT64,std::unique_ptr<Job>>>retired;
 double cpu_ms{};unsigned cpu_frames{};
 void Retire(){const auto done=submit.Completed();if(done==UINT64_MAX)return;while(!retired.empty()&&retired.front().first<=done)retired.pop_front();}
};
inline Runtime*&State(){static Runtime*s=nullptr;return s;}
inline void DumpDebug(ID3D12Device*d){
#if NATIVE_HAVE_SDKLAYERS
 ID3D12InfoQueue*q=nullptr;if(d&&SUCCEEDED(d->QueryInterface(IID_PPV_ARGS(&q)))){auto n=q->GetNumStoredMessages();
  if(FILE*f=_wfopen(NativeLabPath(L"logs\\native-pre-debug.txt").c_str(),L"ab")){for(UINT64 i=n>80?n-80:0;i<n;i++){SIZE_T len=0;q->GetMessage(i,nullptr,&len);std::vector<char>b(len);auto*m=reinterpret_cast<D3D12_MESSAGE*>(b.data());if(len&&SUCCEEDED(q->GetMessage(i,m,&len)))fprintf(f,"[%u/%u] %s\n",unsigned(m->Severity),unsigned(m->ID),m->pDescription?m->pDescription:"");}fclose(f);}q->Release();}
#endif
}
inline bool Process(ID3D12CommandQueue*q,Job&j){
 auto*&s=State();auto d=j.desc;bool processed=false;uint32_t result=~0u;
 try{
 if(!s||s->submit.Queue()!=q){if(s){Log(j.frame,j.desc,"queue changed: retaining old runtime");if(!neural_oneshot.ResetForNewSession("pre-upscale queue changed"))throw std::runtime_error("queue changed during initialization/render");}
  s=new Runtime;s->submit.Create(q,Async(),j.record_device,Async());
 }
 const auto started=std::chrono::steady_clock::now();s->Retire();
 if(s->failed||Fatal().load())throw std::runtime_error("pre-upscale disabled after earlier failure");
 if(j.following_work){Log(j.frame,d,"UNSAFE: draw/dispatch after deferred upscaler in same list");if(Mode()==1)throw std::runtime_error("pre-upscale requires tail-of-list dispatch");}
  if(j.uncertain)throw std::runtime_error("unsupported split/subresource barrier after capture");
  // Unknown terminal states cannot be safely repaired after capture. Stop the
  // experiment rather than guessing the resource's state at the FFX boundary.
  D3D12_RESOURCE_STATES replay_states[7]{};
  for(unsigned i=0;i<7;i++)if(d.resources[i].resource){replay_states[i]=j.states[i];if(!Reverse(j.states[i],d.resources[i].state)){char m[128];snprintf(m,sizeof m,"terminal resource state not representable by FFX (resource %u d3d12 state 0x%x)",i,unsigned(j.states[i]));throw std::runtime_error(m);}}
  auto*color=static_cast<ID3D12Resource*>(d.resources[0].resource);auto*motion=static_cast<ID3D12Resource*>(d.resources[2].resource);auto cd=color->GetDesc();
  if(j.frame<=2){char m[256];snprintf(m,sizeof m,"inputs: color fmt=%u %llux%u motion fmt=%u depth fmt=%u exposure=%s reactive=%s tc=%s output fmt=%u mvscale=%g,%g jitter=%g,%g pre_exposure=%g flags=0x%x",unsigned(cd.Format),(unsigned long long)cd.Width,cd.Height,unsigned(motion->GetDesc().Format),d.resources[1].resource?unsigned(static_cast<ID3D12Resource*>(d.resources[1].resource)->GetDesc().Format):0u,d.resources[3].resource?"yes":"no",d.resources[4].resource?"yes":"no",d.resources[5].resource?"yes":"no",unsigned(static_cast<ID3D12Resource*>(d.resources[6].resource)->GetDesc().Format),d.motion_scale[0],d.motion_scale[1],d.jitter[0],d.jitter[1],d.pre_exposure,d.flags);Log(j.frame,d,m);}
  if(FitLargeFromFile())NativeFitLargeInputOverride()=true;
  bool supported=NativeInputGeometry::Supported(d.render[0],d.render[1],NativeFitLargeInput())&&NativeIsGameColor(cd.Format)&&!(cd.Flags&D3D12_RESOURCE_FLAG_DENY_SHADER_RESOURCE);
  if(Mode()==1&&supported&&!neural_oneshot.Bypassed()){
   bool same=s->low&&s->low->GetDesc().Width==d.render[0]&&s->low->GetDesc().Height==d.render[1]&&s->low->GetDesc().Format==cd.Format;
   if(!same&&s->low){if(neural_oneshot.ResetForNewSession("pre-upscale render geometry changed")){s->submit.Flush();s->low->Release();s->low=nullptr;}else supported=false;}
   if(supported&&!s->low){cd.Width=d.render[0];cd.Height=d.render[1];cd.Layout=D3D12_TEXTURE_LAYOUT_UNKNOWN;cd.Alignment=0;
    D3D12_HEAP_PROPERTIES hp{};hp.Type=D3D12_HEAP_TYPE_DEFAULT;
    if(FAILED(NativeCreateCommittedResource(s->submit.Device(),&hp,D3D12_HEAP_FLAG_NONE,&cd,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE,nullptr,IID_PPV_ARGS(&s->low))))throw std::runtime_error("private low-res allocation");}
   if(supported){
    s->submit.Submit([&](ID3D12GraphicsCommandList*c){Transition(c,color,j.states[0],D3D12_RESOURCE_STATE_COPY_SOURCE);Transition(c,s->low,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE,D3D12_RESOURCE_STATE_COPY_DEST);
     D3D12_TEXTURE_COPY_LOCATION src{},dst{};src.pResource=color;src.Type=D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX;dst.pResource=s->low;dst.Type=D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX;
     D3D12_BOX box{0,0,0,d.render[0],d.render[1],1};c->CopyTextureRegion(&dst,0,0,0,&src,&box);
     Transition(c,s->low,D3D12_RESOURCE_STATE_COPY_DEST,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE);Transition(c,color,D3D12_RESOURCE_STATE_COPY_SOURCE,j.states[0]);});
    const bool wants=neural_oneshot.WantsFrame();const unsigned ph=neural_oneshot.Phase();
    if(wants||ph==0||ph==5){
     if(ph==0||ph==5){NativeMotionVectorScale()[0]=d.motion_scale[0];NativeMotionVectorScale()[1]=d.motion_scale[1];if(Display().notice>=2)s->overlay.Prepare(static_cast<ID3D12Resource*>(d.resources[6].resource));}
     /* reset=true means the network never samples motion/history in this prototype. */
     neural_oneshot.OnSubmitted(q,s->low,motion,true,d.resources[2].width,d.resources[2].height,d.render[0],d.render[1],D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE,true);
     processed=wants&&neural_oneshot.Phase()==4;
    }
    if(processed){d.resources[0].resource=s->low;d.resources[0].width=d.render[0];d.resources[0].height=d.render[1];d.resources[0].state=4;}
   }
  }
  if(Mode()==1&&!supported&&j.frame%100==0)Log(j.frame,d,"unsupported low-res input: FFX only");
  s->submit.Submit([&](ID3D12GraphicsCommandList*c){
   for(unsigned i=0;i<7;i++)if(j.desc.resources[i].resource){bool duplicate=false;for(unsigned k=0;k<i;k++)duplicate|=j.desc.resources[k].resource==j.desc.resources[i].resource;if(!duplicate)Transition(c,static_cast<ID3D12Resource*>(j.desc.resources[i].resource),j.states[i],replay_states[i]);}
   d.command_list=c;Guard guard;if(j.frame<5)Log(j.frame,d,"before original FFX replay");
   if(processed){PrivateBarrierResource()=s->low;PrivateBarrierState()=D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE;}
   result=original(&j.context,&d.header);
   if(processed){PrivateBarrierResource()=nullptr;Transition(c,s->low,PrivateBarrierState(),D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE);}
   if(j.frame<5)Log(j.frame,d,"after original FFX replay",processed,result);
   for(unsigned i=0;i<7;i++)if(j.desc.resources[i].resource){bool duplicate=false;for(unsigned k=0;k<i;k++)duplicate|=j.desc.resources[k].resource==j.desc.resources[i].resource;if(!duplicate)Transition(c,static_cast<ID3D12Resource*>(j.desc.resources[i].resource),replay_states[i],j.states[i]);}
   if(Mode()==1&&Display().notice>=2){
   char text[96],fps[20]="";const double ms=neural_oneshot.AvgMs();if(Display().fps&&processed&&ms>0)snprintf(fps,sizeof fps," %.1f FPS",1000.0/ms);
   const unsigned phase=neural_oneshot.Phase();const char*status=processed?"ON":phase==1?"INIT":phase==5?"ERROR":!supported?"UNSUPPORTED":"OFF";
   snprintf(text,sizeof text,"DLSS5 %s %ux%u -> FSR %ux%u%s",status,d.render[0],d.render[1],d.upscale[0]?d.upscale[0]:d.resources[6].width,d.upscale[1]?d.upscale[1]:d.resources[6].height,fps);
   s->overlay.Draw(c,static_cast<ID3D12Resource*>(d.resources[6].resource),text,24,24,3,j.states[6]);
   }
  });
  if(j.frame<5||j.frame%100==0||result)Log(j.frame,d,Mode()==2?"FFX-only smoke replay":"replayed",processed,result);
  s->cpu_ms+=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-started).count();
  if(++s->cpu_frames%100==0){if(FILE*f=_wfopen(NativeLabPath(L"logs\\native-pre-upscale.txt").c_str(),L"ab")){fprintf(f,"pid=%lu frame=%u async=%u submit_cpu_ms=%.3f retained=%zu\n",GetCurrentProcessId(),j.frame,unsigned(s->submit.Deferred()),s->cpu_ms/100,s->retired.size());fclose(f);}s->cpu_ms=0;}
  if(result)throw std::runtime_error("FFX replay returned error");return true;
 }catch(const std::exception&e){PrivateBarrierResource()=nullptr;Fatal().store(true);if(s){s->failed=true;DumpDebug(s->submit.Device());}Log(j.frame,d,e.what(),processed,result);return false;}
}
inline bool Execute(ID3D12CommandQueue*q,UINT count,ID3D12CommandList*const*lists,ExecuteLists real_execute){
 if(!HasPendingJobs()||Replaying()||!q||!lists||!real_execute||q->GetDesc().Type!=D3D12_COMMAND_LIST_TYPE_DIRECT)return false;
 std::vector<std::pair<UINT,std::unique_ptr<Job>>>jobs;
 {std::lock_guard<std::mutex>lock(Mutex());for(UINT i=0;i<count;i++){auto it=Jobs().find(static_cast<ID3D12GraphicsCommandList*>(lists[i]));if(it!=Jobs().end()){jobs.emplace_back(i,std::move(it->second));Jobs().erase(it);}}PendingJobs().store(!Jobs().empty(),std::memory_order_release);}
 if(jobs.empty())return false;
 static std::mutex execution;std::lock_guard<std::mutex>lock(execution);Guard guard;UINT begin=0;
 for(auto&entry:jobs){const UINT end=entry.first+1;real_execute(q,end-begin,lists+begin);begin=end;
  if(!Process(q,*entry.second)){// Timeout is not cancellation: deliberately retain all GPU references.
   Fatal().store(true);Log(entry.second->frame,entry.second->desc,"fatal: future captures disabled; forwarding remaining game lists");
   entry.second.release();for(auto&remaining:jobs)remaining.second.release();
   if(begin<count)real_execute(q,count-begin,lists+begin);return true;
  }
  if(State()->submit.Deferred())State()->retired.emplace_back(State()->submit.LastValue(),std::move(entry.second));
 }
 if(begin<count)real_execute(q,count-begin,lists+begin);return true;
}
} // namespace NativePreUpscale
