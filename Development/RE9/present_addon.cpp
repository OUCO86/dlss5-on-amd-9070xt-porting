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
#include "native_only.h"
static bool native_settings=false;
static void env(const std::string&k,const std::string&v){_putenv_s(k.c_str(),v.c_str());std::wstring wk(k.begin(),k.end()),wv(v.begin(),v.end());_wputenv_s(wk.c_str(),wv.c_str());}
static void flags(){std::ifstream f(NativeLabPath(L"native-game-flags.txt").c_str());std::string s;while(std::getline(f,s)){if(!s.empty()&&s.back()=='\r')s.pop_back();auto p=s.find('=');if(s.rfind("DLSS5_",0)==0&&p!=std::string::npos)env(s.substr(0,p),s.substr(p+1));}env("DLSS5_CODEC_SRGB","1");env("DLSS5_OVERLAP","0");env("DLSS5_GAME_PROBE","0");env("DLSS5_SHOW_FPS","0");env("DLSS5_NETWORK_HEIGHT","900");}
struct Runtime{ID3D12CommandQueue*q{};Re9PresentBridge bridge;NativeGameFrame frame;std::atomic<int>init{0};unsigned frames{};bool failed{};~Runtime(){if(q)q->Release();}};
// Keep failed/initializing instances alive: a timed-out GPU submission is not cancellation.
static Runtime* active{};static reshade::api::swapchain* owner{};static std::mutex gate;static bool bypass{},key{};static int mode=2;static ULONGLONG poll{};
// Draw after inference, including bypass/init notices; never feed the information strip to HIP.
static bool info_hidden{},info_key{};static unsigned show_fps=1,show_notice=2;
struct InfoOverlay {
 ID3D12CommandQueue*q{};NativeGameSubmission submit;NativeTextOverlay status,fps;
 explicit InfoOverlay(ID3D12CommandQueue*queue,ID3D12Resource*back):q(queue){submit.Create(q,false);status.Prepare(back);fps.Prepare(back);}
};
static InfoOverlay*info{};static ULONGLONG fps_start{};static unsigned fps_count{};static double present_fps{};
struct PresentInfo {
 ID3D12Resource*back;ID3D12CommandQueue*q;const char*state="OFF";bool safe=true;bool supported=true;
 ~PresentInfo(){
  if(!safe||info_hidden||(!show_notice&&!show_fps))return;
  try{
   if(info&&info->q!=q){delete info;info=nullptr;}
   if(!info)info=new InfoOverlay(q,back);
   auto d=back->GetDesc();char a[100]{},b[100]{};
   if(supported&&active&&active->init==2){const auto g=NativeCurrentNetworkGeometry();snprintf(a,sizeof a,"DLSS5 POST: %s  NET %uX%u  OUT %uX%u",state,g.valid_width,g.valid_height,unsigned(d.Width),d.Height);}
   else snprintf(a,sizeof a,"DLSS5 POST: %s  OUT %uX%u",state,unsigned(d.Width),d.Height);
   snprintf(b,sizeof b,"PRESENT %.1f FPS  F6 ON/OFF  F7 INFO",present_fps);
   const UINT x=d.Width>828?UINT(d.Width)-804:24;
   info->submit.Submit([&](ID3D12GraphicsCommandList*c){if(show_notice)info->status.Draw(c,back,a,x,96,2,D3D12_RESOURCE_STATE_PRESENT);if(show_fps)info->fps.Draw(c,back,b,x,120,2,D3D12_RESOURCE_STATE_PRESENT);});
  }catch(const std::exception&e){log(std::string("overlay disabled: ")+e.what());info_hidden=true;}
 }
};
static bool snapshot=false;
static void dump(const wchar_t*name,const std::vector<unsigned char>&v){std::ofstream f(NativeLabPath(name).c_str(),std::ios::binary);f.write((const char*)v.data(),v.size());}
static void present(reshade::api::command_queue*queue,reshade::api::swapchain*swap,const reshade::api::rect*,const reshade::api::rect*,uint32_t,const reshade::api::rect*){
 if(queue->get_device()->get_api()!=reshade::api::device_api::d3d12)return;
 std::lock_guard<std::mutex>lock(gate);bool down=(GetAsyncKeyState(VK_F6)&0x8000)!=0;if(down&&!key){bypass=!bypass;log(bypass?"F6 bypass":"F6 enabled");}key=down;bool ik=(GetAsyncKeyState(VK_F7)&0x8000)!=0;if(ik&&!info_key){info_hidden=!info_hidden;log(info_hidden?"info hidden":"info shown");}info_key=ik;
 auto now=GetTickCount64();if(!fps_start)fps_start=now;++fps_count;if(now-fps_start>=1000){present_fps=1000.0*fps_count/double(now-fps_start);fps_count=0;fps_start=now;}
 if(GetTickCount64()-poll>1000){poll=GetTickCount64();native_settings=Re9NativeSettings();show_fps=1;show_notice=2;if(FILE*f=_wfopen(NativeLabPath(L"native-game-flags.txt").c_str(),L"rb")){char line[256];while(fgets(line,sizeof line,f)){unsigned v;if(sscanf(line,"DLSS5_SHOW_FPS=%u",&v)==1)show_fps=v;if(sscanf(line,"DLSS5_NOTICE=%u",&v)==1)show_notice=v;if(sscanf(line,"DLSS5_RE9_SNAPSHOT=%u",&v)==1)snapshot=v!=0;}fclose(f);}int next=2;if(FILE*f=_wfopen(NativeLabPath(L"re9-present-mode.txt").c_str(),L"rb")){fscanf(f,"%d",&next);fclose(f);}if(next!=mode){mode=next;log("mode="+std::to_string(mode));}}

 auto*q=reinterpret_cast<ID3D12CommandQueue*>(queue->get_native());auto*sc=reinterpret_cast<IDXGISwapChain3*>(swap->get_native());if(!sc)return;ID3D12Resource*back=nullptr;if(FAILED(sc->GetBuffer(sc->GetCurrentBackBufferIndex(),IID_PPV_ARGS(&back))))return;std::unique_ptr<ID3D12Resource,void(*)(ID3D12Resource*)> hold(back,[](ID3D12Resource*p){p->Release();});if(!q||!back||q->GetDesc().Type!=D3D12_COMMAND_LIST_TYPE_DIRECT)return;
 PresentInfo hud{back,q};
 auto d=back->GetDesc();if(d.Format!=DXGI_FORMAT_R10G10B10A2_UNORM||d.Width>1920||d.Height>1080||!d.Width||!d.Height||d.SampleDesc.Count!=1||swap->get_color_space()!=reshade::api::color_space::srgb_nonlinear){hud.supported=false;hud.state=(d.Width>1920||d.Height>1080)?"ERROR MAX 1920X1080":"SDR R10 REQUIRED";if(swap->get_color_space()!=reshade::api::color_space::srgb_nonlinear)hud.safe=false;static bool warned=false;if(!warned){warned=true;log("unsupported format/size/colorspace format="+std::to_string(d.Format)+" size="+std::to_string(d.Width)+"x"+std::to_string(d.Height)+" space="+std::to_string(int(swap->get_color_space())));}return;}
 if(bypass||mode<0||mode>1)return;
 const auto last_upscale=re9_upscale_tick.load();
 if(!native_settings||(last_upscale&&GetTickCount64()-last_upscale<1000)){hud.supported=false;hud.state="ERROR TURN OFF GAME UPSCALING";return;}
 try{
 if(active&&(owner!=swap||active->q!=q||!active->bridge.Matches(back))){if(active->init==1){hud.state="INITIALIZING";return;}if(!active->failed&&active->init!=3)delete active;active=nullptr;}
 if(!active){active=new Runtime;owner=swap;active->q=q;q->AddRef();active->bridge.Create(q,UINT(d.Width),d.Height);log("bridge ready "+std::to_string(d.Width)+"x"+std::to_string(d.Height));}
 auto*r=active;if(r->failed){hud.safe=false;return;}if(r->init==3){hud.state="INIT FAILED - SEE LOGS";return;}
 if(mode==1&&r->init==0){hud.state="INITIALIZING";if(!info)info=new InfoOverlay(q,back);r->init=1;std::thread([r]{try{flags();auto noise=NativeReadF32(NativeLabPath(L"native-game-tiled-assets\\noise.f32"),"noise");r->frame.Create(r->q,r->bridge.Color(),noise,NativeLabPath(L"native-game-tiled-assets"));r->frame.SuppressFps();log("HIP ready");r->init=2;}catch(const std::exception&e){log(std::string("init failed: ")+e.what());r->init=3;}}).detach();return;}
 if(r->init==1){hud.state="INITIALIZING";return;}
 hud.state=mode==1?"ON":"CONVERSION";
 r->bridge.Read(back);
 if(mode==1){if(snapshot&&r->frames==0)dump(L"logs\\re9-present-before.rgba16f",NativeReadSubmittedFrame(q,r->bridge.Color(),D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE));r->frame.ProcessSubmittedFrame(r->bridge.Color(),D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE,0,false,nullptr,true);if(snapshot&&r->frames==0)dump(L"logs\\re9-present-after.rgba16f",NativeReadSubmittedFrame(q,r->bridge.Color(),D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE));}
 r->bridge.Write(back);if(mode==1){++r->frames;if(r->frames==1||r->frames%300==0)log("HIP processed="+std::to_string(r->frames));}else{static bool noted=false;if(!noted){noted=true;log("conversion roundtrip presented");}}
 }catch(const std::exception&e){hud.safe=false;if(active)active->failed=true;log(std::string("disabled after failure: ")+e.what());}
}
BOOL WINAPI DllMain(HINSTANCE h,DWORD reason,LPVOID){if(reason==DLL_PROCESS_ATTACH){DisableThreadLibraryCalls(h);if(!reshade::register_addon(h))return FALSE;HMODULE pinned{};if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,reinterpret_cast<LPCWSTR>(&present),&pinned))return FALSE;reshade::register_event<reshade::addon_event::present>(present);HANDLE worker=CreateThread(nullptr,0,Re9ObserveWorker,nullptr,0,nullptr);if(worker)CloseHandle(worker);}return TRUE;}
