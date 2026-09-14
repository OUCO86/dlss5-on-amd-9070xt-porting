#pragma once
#include "../Development/HIP/hip_d3d12_bridge.h"
#include "native_network_geometry.h"
// Experimental compile-time backend. Ordinary D3D12 codec and temporal passes stay in NativeGameFrame.
class NativeHipNetwork {
 hip_reference::D3D12Bridge bridge;ID3D12Resource*color{};ID3D12Resource*history{};
 static std::string Utf8(const std::wstring&s){int n=WideCharToMultiByte(CP_UTF8,0,s.data(),int(s.size()),nullptr,0,nullptr,nullptr);if(!n&&!s.empty())throw std::runtime_error("HIP path encoding");std::string r(n,'\0');if(n)WideCharToMultiByte(CP_UTF8,0,s.data(),int(s.size()),r.data(),n,nullptr,nullptr);return r;}
public:
 NativeHipNetwork()=default;NativeHipNetwork(const NativeHipNetwork&)=delete;
 ~NativeHipNetwork(){if(color)color->Release();if(history)history->Release();}
 void Create(ID3D12CommandQueue*q,ID3D12Resource*rgb,const std::vector<float>&noise,const std::wstring&directory,ID3D12Resource*temporal,UINT post_shift){
  if(color||!rgb)throw std::runtime_error("HIP network initialization");auto g=NativeCurrentNetworkGeometry();hip_reference::Options o;o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift;o.fast_vit=true;o.wmma=o.wave=o.tiled=o.pooled=true;o.assets=Utf8(directory);if(const wchar_t*skip=_wgetenv(L"DLSS5_SKIP_BLOCKS"))o.skip_blocks=hip_reference::ParseSkipBlocks(Utf8(skip));
  const wchar_t*modules=_wgetenv(L"DLSS5_HIP_MODULES");o.modules=Utf8(modules&&*modules?std::wstring(modules):directory+L"\\HIP");bridge.Create(q,o,noise);color=rgb;color->AddRef();history=temporal;if(history)history->AddRef();
 }
 template<class Submission>void Run(Submission&submit,UINT seed,bool use_history=false){if(use_history&&!history)throw std::runtime_error("HIP history not bound");bridge.Run(submit,color,use_history?history:nullptr,seed);}
 ID3D12Resource*Output()const{return bridge.Output();}
};
