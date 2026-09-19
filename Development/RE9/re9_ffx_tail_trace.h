#pragma once
// Diagnostic only: observe commands after a normally recorded FFX dispatch.
// Never suppress, close, reset, or submit a game-owned command list.
namespace Re9FfxTrace {
struct Entry {unsigned frame{},events{};};
inline std::mutex mutex;
inline std::unordered_map<void*,Entry> lists;
inline std::atomic<bool> active{false};
inline void Arm(void*list,unsigned frame,const Header*h){
 if(!list||frame>16)return;
 NativePreUpscale::Description d{};if(!NativePreUpscale::Read(h,&d,sizeof d))return;
 std::lock_guard<std::mutex> guard(mutex);lists[list]={frame,0};active=true;
 if(FILE*f=_wfopen(NativeLabPath(L"logs\\re9-ffx-tail.txt").c_str(),L"ab")){
  fprintf(f,"frame=%u after_original_ffx list=%p list_type=%u render=%ux%u upscale=%ux%u output=%p\n",frame,list,unsigned(static_cast<ID3D12GraphicsCommandList*>(list)->GetType()),d.render[0],d.render[1],d.upscale[0],d.upscale[1],d.resources[6].resource);fclose(f);
 }
}
inline void Work(void*list,const char*kind){
 if(!active.load(std::memory_order_relaxed))return;
 std::lock_guard<std::mutex> guard(mutex);auto it=lists.find(list);if(it==lists.end())return;
 unsigned index=++it->second.events;if(index>4)return;
 if(FILE*f=_wfopen(NativeLabPath(L"logs\\re9-ffx-tail.txt").c_str(),L"ab")){
  fprintf(f,"frame=%u following=%u kind=%s list=%p thread=%lu\n",it->second.frame,index,kind,list,GetCurrentThreadId());
  void*stack[20]{};USHORT n=CaptureStackBackTrace(1,20,stack,nullptr);
  for(USHORT i=0;i<n;i++){HMODULE mod=nullptr;wchar_t path[MAX_PATH]{};GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,reinterpret_cast<LPCWSTR>(stack[i]),&mod);if(mod)GetModuleFileNameW(mod,path,MAX_PATH);const wchar_t*name=wcsrchr(path,L'\\');fprintf(f,"  %ls+%llx\n",name?name+1:path,(unsigned long long)(reinterpret_cast<uintptr_t>(stack[i])-reinterpret_cast<uintptr_t>(mod)));}fclose(f);
 }
}
inline void Close(void*list){
 if(!active.load(std::memory_order_relaxed))return;
 std::lock_guard<std::mutex> guard(mutex);auto it=lists.find(list);if(it==lists.end())return;
 if(FILE*f=_wfopen(NativeLabPath(L"logs\\re9-ffx-tail.txt").c_str(),L"ab")){fprintf(f,"frame=%u close following_total=%u list=%p\n",it->second.frame,it->second.events,list);fclose(f);}
 lists.erase(it);active=!lists.empty();
}
// Observe the outer NGX boundary too: OptiScaler may call a Detours trampoline for FFX.
using NgxEvaluate=uint32_t(*)(ID3D12GraphicsCommandList*,const void*,const void*,void*);
inline NgxEvaluate ngx_original[2]{};
inline std::atomic<unsigned> ngx_frames{};
inline thread_local unsigned ngx_depth{};
template<unsigned Slot>uint32_t Ngx(ID3D12GraphicsCommandList*list,const void*handle,const void*parameters,void*callback){
 struct Depth{Depth(){++ngx_depth;}~Depth(){--ngx_depth;}} depth;
 auto result=ngx_original[Slot](list,handle,parameters,callback);
 if(ngx_depth!=1||!list)return result;
 unsigned frame=++ngx_frames;if(frame>16)return result;
 ID3D12GraphicsCommandList*native=nullptr;
 if(FAILED(list->QueryInterface(UnwrappedObject,reinterpret_cast<void**>(&native)))||!native){native=list;native->AddRef();}
 {std::lock_guard<std::mutex> guard(mutex);lists[native]={frame,0};active=true;
  if(FILE*f=_wfopen(NativeLabPath(L"logs\\re9-ffx-tail.txt").c_str(),L"ab")){fprintf(f,"frame=%u after_original_ngx list=%p list_type=%u result=%08x\n",frame,native,unsigned(native->GetType()),result);fclose(f);}}
 native->Release();return result;
}
inline void InstallNgx(){
 using EnumModules=BOOL(WINAPI*)(HANDLE,HMODULE*,DWORD,LPDWORD);
 auto enumerate=reinterpret_cast<EnumModules>(GetProcAddress(GetModuleHandleW(L"kernel32.dll"),"K32EnumProcessModules"));
 if(!enumerate)return;HMODULE modules[1024]{};DWORD bytes=0;if(!enumerate(GetCurrentProcess(),modules,sizeof modules,&bytes))return;
 for(unsigned i=0;i<bytes/sizeof(HMODULE)&&i<1024;i++){
  wchar_t path[MAX_PATH]{};GetModuleFileNameW(modules[i],path,MAX_PATH);const wchar_t*name=wcsrchr(path,L'\\');name=name?name+1:path;
  if(_wcsicmp(name,L"dxgi.dll")&&_wcsicmp(name,L"OptiScaler.dll"))continue;
  void*prior=nullptr;
  for(unsigned slot=0;slot<1;slot++){
   auto target=reinterpret_cast<void*>(GetProcAddress(modules[i],slot?"NVSDK_NGX_D3D12_EvaluateFeature_C":"NVSDK_NGX_D3D12_EvaluateFeature"));if(!target||target==prior)continue;
   auto hook=slot?reinterpret_cast<void*>(&Ngx<1>):reinterpret_cast<void*>(&Ngx<0>);
   auto status=MH_CreateHook(target,hook,reinterpret_cast<void**>(&ngx_original[slot]));if(status==MH_OK)status=MH_EnableHook(target);
   if(FILE*f=_wfopen(NativeLabPath(L"logs\\re9-ffx-tail.txt").c_str(),L"ab")){fprintf(f,"ngx_hook slot=%u status=%u module=%ls target=%p\n",slot,unsigned(status),path,target);fclose(f);}
   if(status==MH_OK)prior=target;
  }
 }
}

}
