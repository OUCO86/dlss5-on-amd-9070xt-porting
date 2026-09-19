#pragma once
#include <MinHook.h>
#include <atomic>
// Observe NGX without changing the game's rendering. Recent evaluation rejects unsaved DLSS changes too.
inline std::atomic<ULONGLONG> re9_upscale_tick{};
using Re9Ngx=uint32_t(*)(ID3D12GraphicsCommandList*,const void*,const void*,void*);
inline Re9Ngx re9_ngx_original{};
inline uint32_t Re9ObserveNgx(ID3D12GraphicsCommandList*l,const void*h,const void*p,void*c){re9_upscale_tick=GetTickCount64();return re9_ngx_original(l,h,p,c);}
inline DWORD WINAPI Re9ObserveWorker(void*){
 auto status=MH_Initialize();if(status!=MH_OK&&status!=MH_ERROR_ALREADY_INITIALIZED)return 0;
 for(;;){
  for(const wchar_t*name:{L"dxgi.dll",L"OptiScaler.dll"})if(auto m=GetModuleHandleW(name)){
   auto target=reinterpret_cast<void*>(GetProcAddress(m,"NVSDK_NGX_D3D12_EvaluateFeature"));if(!target)continue;
   auto result=MH_CreateHook(target,reinterpret_cast<void*>(&Re9ObserveNgx),reinterpret_cast<void**>(&re9_ngx_original));
   if(result==MH_OK){result=MH_EnableHook(target);log("native-only NGX guard="+std::to_string(result));return 0;}
  }
  Sleep(500);
 }
}
inline bool Re9NativeSettings(){
 wchar_t path[MAX_PATH]{};GetModuleFileNameW(nullptr,path,MAX_PATH);std::wstring file(path);auto slash=file.find_last_of(L"\\/");if(slash==std::wstring::npos)return false;file.resize(slash);file+=L"\\config.ini";
 wchar_t value[64]{};GetPrivateProfileStringW(L"GameOption",L"UpscalingAlgorithm",L"",value,64,file.c_str());
 // Fail closed for unknown/missing modes; validated against the game's saved native setting.
 return !_wcsicmp(value,L"None");
}
