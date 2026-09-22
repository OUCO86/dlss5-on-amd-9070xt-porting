#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <d3d12.h>
#include <dxgi1_4.h>
#include <cstdio>
#include <cstdlib>
#include <LmxxfNrApi.h>
static void ck(HRESULT h){if(FAILED(h)){printf("D3D failure %08lx\n",(unsigned long)h);exit(2);}}
int wmain(int argc,wchar_t**argv){
 if(argc!=6)return 2;setvbuf(stdout,nullptr,_IONBF,0);
 const bool prime=wcstol(argv[3],nullptr,10)!=0;UINT w=wcstol(argv[4],nullptr,10),h=wcstol(argv[5],nullptr,10);
 auto dll=LoadLibraryW(argv[1]);if(!dll)return 3;
 auto get=(int32_t(*)(uint32_t,LmxxfNrApi*))GetProcAddress(dll,"LmxxfNrGetApi");
 LmxxfNrApi api{};api.struct_size=sizeof api;if(!get||get(2,&api))return 4;
 IDXGIFactory4*f{};ck(CreateDXGIFactory1(IID_PPV_ARGS(&f)));ID3D12Device*d{};
 for(UINT i=0;;++i){IDXGIAdapter1*a{};if(f->EnumAdapters1(i,&a)==DXGI_ERROR_NOT_FOUND)break;DXGI_ADAPTER_DESC1 ad{};a->GetDesc1(&ad);if(ad.VendorId==0x1002)D3D12CreateDevice(a,D3D_FEATURE_LEVEL_12_0,IID_PPV_ARGS(&d));a->Release();if(d)break;}f->Release();if(!d)return 5;
 ID3D12CommandQueue*q{};D3D12_COMMAND_QUEUE_DESC qd{};ck(d->CreateCommandQueue(&qd,IID_PPV_ARGS(&q)));
 void*ctx{};LmxxfNrCreateInfo ci{};ci.struct_size=sizeof ci;ci.device=d;ci.queue=q;ci.assets_directory=argv[2];if(api.Create(&ci,&ctx)||api.PrepareSession(ctx))return 6;
 auto attempt=[&](UINT x,UINT y,bool record){
  ID3D12Resource*r{};D3D12_HEAP_PROPERTIES hp{};hp.Type=D3D12_HEAP_TYPE_DEFAULT;D3D12_RESOURCE_DESC td{};td.Dimension=D3D12_RESOURCE_DIMENSION_TEXTURE2D;td.Width=x;td.Height=y;td.MipLevels=td.DepthOrArraySize=1;td.SampleDesc.Count=1;td.Format=DXGI_FORMAT_R9G9B9E5_SHAREDEXP;ck(d->CreateCommittedResource(&hp,D3D12_HEAP_FLAG_NONE,&td,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE,nullptr,IID_PPV_ARGS(&r)));
  LmxxfNrFrameInfo fi{};fi.struct_size=sizeof fi;fi.color=r;fi.color_width=x;fi.color_height=y;fi.color_state=D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE;fi.pre_exposure=fi.exposure_scale=fi.model_scale=1;LmxxfNrJob j{};j.struct_size=sizeof j;
  auto rc=api.PrepareFrame(ctx,&fi,&j);char err[1024]{};api.GetLastError(err,sizeof err);printf("PrepareFrame %ux%u rc=%d error=%s\n",x,y,rc,err);
  if(!rc&&record){ID3D12CommandAllocator*al{};ID3D12GraphicsCommandList*cl{};ck(d->CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_DIRECT,IID_PPV_ARGS(&al)));ck(d->CreateCommandList(0,D3D12_COMMAND_LIST_TYPE_DIRECT,al,nullptr,IID_PPV_ARGS(&cl)));rc=api.RecordInputs(ctx,j.handle,cl);api.GetLastError(err,sizeof err);printf("RecordInputs %ux%u rc=%d error=%s\n",x,y,rc,err);ck(cl->Close());cl->Release();al->Release();}
  r->Release();return rc;
 };
 printf("CASE prime=%d valid=%ux%u (record only; no producer/consumer submission)\n",prime,w,h);
 if(prime)attempt(2560,1080,false);
 int result=attempt(w,h,true);printf("Destroy rc=%d\n",api.Destroy(ctx));printf("device_removed=%08lx result=%d\n",(unsigned long)d->GetDeviceRemovedReason(),result);q->Release();d->Release();FreeLibrary(dll);return 0;
}
