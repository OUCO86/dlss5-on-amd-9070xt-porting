#include "present_bridge.h"
#include "../../src/native_game_frame.h"
#include <reshade.hpp>
#include <atomic>
#include <dxgi1_4.h>
#include <memory>
#include <fstream>
extern "C" __declspec(dllexport) const char* NAME="DLSS5 AMD RE9 post-present";
extern "C" __declspec(dllexport) const char* DESCRIPTION="Experimental SDR post-processing on an owned command list; F6 bypass.";
static void log(const std::string&s){if(FILE*f=_wfopen(NativeLabPath(L"logs\\re9-present.txt").c_str(),L"ab")){fprintf(f,"pid=%lu tick=%llu %s\n",GetCurrentProcessId(),GetTickCount64(),s.c_str());fclose(f);}}
static void env(const std::string&k,const std::string&v){_putenv_s(k.c_str(),v.c_str());std::wstring wk(k.begin(),k.end()),wv(v.begin(),v.end());_wputenv_s(wk.c_str(),wv.c_str());}
static void flags(){std::ifstream f(NativeLabPath(L"native-game-flags.txt").c_str());std::string s;while(std::getline(f,s)){if(!s.empty()&&s.back()=='\r')s.pop_back();auto p=s.find('=');if(s.rfind("DLSS5_",0)==0&&p!=std::string::npos)env(s.substr(0,p),s.substr(p+1));}env("DLSS5_CODEC_SRGB","1");env("DLSS5_OVERLAP","0");env("DLSS5_GAME_PROBE","0");env("DLSS5_SHOW_FPS","0");env("DLSS5_NETWORK_HEIGHT","900");}
struct Runtime{ID3D12CommandQueue*q{};Re9PresentBridge bridge;NativeGameFrame frame;std::atomic<int>init{0};unsigned frames{};bool failed{};~Runtime(){if(q)q->Release();}};
// Keep failed/initializing instances alive: a timed-out GPU submission is not cancellation.
static Runtime* active{};static reshade::api::swapchain* owner{};static std::mutex gate;static bool bypass{},key{};static int mode=2;static ULONGLONG poll{};
static void dump(const wchar_t*name,const std::vector<unsigned char>&v){std::ofstream f(NativeLabPath(name).c_str(),std::ios::binary);f.write((const char*)v.data(),v.size());}
static void present(reshade::api::command_queue*queue,reshade::api::swapchain*swap,const reshade::api::rect*,const reshade::api::rect*,uint32_t,const reshade::api::rect*){
 if(queue->get_device()->get_api()!=reshade::api::device_api::d3d12)return;
 std::lock_guard<std::mutex>lock(gate);bool down=(GetAsyncKeyState(VK_F6)&0x8000)!=0;if(down&&!key){bypass=!bypass;log(bypass?"F6 bypass":"F6 enabled");}key=down;
 if(GetTickCount64()-poll>1000){poll=GetTickCount64();int next=2;if(FILE*f=_wfopen(NativeLabPath(L"re9-present-mode.txt").c_str(),L"rb")){fscanf(f,"%d",&next);fclose(f);}if(next!=mode){mode=next;log("mode="+std::to_string(mode));}}
 if(bypass||mode<0||mode>1)return;
 auto*q=reinterpret_cast<ID3D12CommandQueue*>(queue->get_native());auto*sc=reinterpret_cast<IDXGISwapChain3*>(swap->get_native());if(!sc)return;ID3D12Resource*back=nullptr;if(FAILED(sc->GetBuffer(sc->GetCurrentBackBufferIndex(),IID_PPV_ARGS(&back))))return;std::unique_ptr<ID3D12Resource,void(*)(ID3D12Resource*)> hold(back,[](ID3D12Resource*p){p->Release();});if(!q||!back||q->GetDesc().Type!=D3D12_COMMAND_LIST_TYPE_DIRECT)return;
 auto d=back->GetDesc();if(d.Format!=DXGI_FORMAT_R10G10B10A2_UNORM||d.Width>1920||d.Height>1080||!d.Width||!d.Height||d.SampleDesc.Count!=1||swap->get_color_space()!=reshade::api::color_space::srgb_nonlinear){static bool warned=false;if(!warned){warned=true;log("unsupported format/size/colorspace format="+std::to_string(d.Format)+" size="+std::to_string(d.Width)+"x"+std::to_string(d.Height)+" space="+std::to_string(int(swap->get_color_space())));}return;}
 try{
 if(active&&(owner!=swap||active->q!=q||!active->bridge.Matches(back))){if(active->init==1)return;if(!active->failed&&active->init!=3)delete active;active=nullptr;}
 if(!active){active=new Runtime;owner=swap;active->q=q;q->AddRef();active->bridge.Create(q,UINT(d.Width),d.Height);log("bridge ready "+std::to_string(d.Width)+"x"+std::to_string(d.Height));}
 auto*r=active;if(r->failed||r->init==3)return;
 if(mode==1&&r->init==0){r->init=1;std::thread([r]{try{flags();auto noise=NativeReadF32(NativeLabPath(L"native-game-tiled-assets\\noise.f32"),"noise");r->frame.Create(r->q,r->bridge.Color(),noise,NativeLabPath(L"native-game-tiled-assets"));r->frame.SuppressFps();log("HIP ready");r->init=2;}catch(const std::exception&e){log(std::string("init failed: ")+e.what());r->init=3;}}).detach();return;}
 if(r->init==1)return;
 r->bridge.Read(back);
 if(mode==1){if(r->frames==0)dump(L"logs\\re9-present-before.rgba16f",NativeReadSubmittedFrame(q,r->bridge.Color(),D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE));r->frame.ProcessSubmittedFrame(r->bridge.Color(),D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE,0,false,nullptr,true);if(r->frames==0)dump(L"logs\\re9-present-after.rgba16f",NativeReadSubmittedFrame(q,r->bridge.Color(),D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE));}
 r->bridge.Write(back);if(mode==1){++r->frames;if(r->frames==1||r->frames%300==0)log("HIP processed="+std::to_string(r->frames));}else{static bool noted=false;if(!noted){noted=true;log("conversion roundtrip presented");}}
 }catch(const std::exception&e){if(active)active->failed=true;log(std::string("disabled after failure: ")+e.what());}
}
BOOL WINAPI DllMain(HINSTANCE h,DWORD reason,LPVOID){if(reason==DLL_PROCESS_ATTACH){DisableThreadLibraryCalls(h);if(!reshade::register_addon(h))return FALSE;HMODULE pinned{};if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,reinterpret_cast<LPCWSTR>(&present),&pinned))return FALSE;reshade::register_event<reshade::addon_event::present>(present);}return TRUE;}
