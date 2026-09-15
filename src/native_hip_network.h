#pragma once
#include "../Development/HIP/hip_d3d12_bridge.h"
#include "native_network_geometry.h"
#include "native_lab_paths.h"
// Experimental compile-time backend. Ordinary D3D12 codec and temporal passes stay in NativeGameFrame.
class NativeHipNetwork {
 hip_reference::D3D12Bridge bridge;ID3D12Resource*color{};ID3D12Resource*history{};
 static std::string Utf8(const std::wstring&s){int n=WideCharToMultiByte(CP_UTF8,0,s.data(),int(s.size()),nullptr,0,nullptr,nullptr);if(!n&&!s.empty())throw std::runtime_error("HIP path encoding");std::string r(n,'\0');if(n)WideCharToMultiByte(CP_UTF8,0,s.data(),int(s.size()),r.data(),n,nullptr,nullptr);return r;}
public:
 NativeHipNetwork()=default;NativeHipNetwork(const NativeHipNetwork&)=delete;
 ~NativeHipNetwork(){if(color)color->Release();if(history)history->Release();}
 void Create(ID3D12CommandQueue*q,ID3D12Resource*rgb,const std::vector<float>&noise,const std::wstring&directory,ID3D12Resource*temporal,UINT post_shift){
  if(color||!rgb)throw std::runtime_error("HIP network initialization");auto g=NativeCurrentNetworkGeometry();hip_reference::Options o;o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift;o.fast_vit=true;o.wmma=o.wave=o.tiled=o.pooled=true;o.assets=Utf8(directory);if(const char*skip=std::getenv("DLSS5_SKIP_BLOCKS"))o.skip_blocks=hip_reference::ParseSkipBlocks(skip);
  bool fast=false;if(const char*value=std::getenv("DLSS5_HIP_FAST")){if(strcmp(value,"0")&&strcmp(value,"1"))throw std::runtime_error("DLSS5_HIP_FAST must be 0 or 1");fast=!strcmp(value,"1");}
  if(fast)o.fast_c32=o.fused_c32=o.fused_ffn=o.fast_mh=o.fused_mh=o.mh_wave=o.fast_deep=o.fast_prefix=o.packed_weights=o.packed_c32=o.fp8_normalized=o.fp8_ffn=o.fp8_av=o.fp8_deep=o.fp8_middle=o.half_c32=o.crop_c32=true;
  if(const char*v=std::getenv("DLSS5_HIP_GRAPH")){if(strcmp(v,"0")&&strcmp(v,"1"))throw std::runtime_error("DLSS5_HIP_GRAPH must be 0 or 1");o.graph=!strcmp(v,"1");}
  const char*modules=std::getenv("DLSS5_HIP_MODULES");o.modules=modules&&*modules?std::string(modules):Utf8(directory+L"\\HIP");bridge.Create(q,o,noise);
  if(FILE*f=_wfopen(NativeLabPath(L"logs\\native-hip.txt").c_str(),L"ab")){fprintf(f,"pid=%lu runtime=7 fast=%u packed_weights=%u packed_c32=%u fp8_normalized=%u fp8_ffn=%u fp8_av=%u fp8_deep=%u fp8_middle=%u half_c32=%u crop_c32=%u graph=%u processing=%ux%u modules=%s\n",GetCurrentProcessId(),unsigned(fast),unsigned(o.packed_weights),unsigned(o.packed_c32),unsigned(o.fp8_normalized),unsigned(o.fp8_ffn),unsigned(o.fp8_av),unsigned(o.fp8_deep),unsigned(o.fp8_middle),unsigned(o.half_c32),unsigned(o.crop_c32),unsigned(o.graph),o.width,o.height,o.modules.c_str());fclose(f);}
color=rgb;color->AddRef();history=temporal;if(history)history->AddRef();
 }
 template<class Submission>void Run(Submission&submit,UINT seed,bool use_history=false){if(use_history&&!history)throw std::runtime_error("HIP history not bound");bridge.Run(submit,color,use_history?history:nullptr,seed);}
 ID3D12Resource*Output()const{return bridge.Output();}
};
