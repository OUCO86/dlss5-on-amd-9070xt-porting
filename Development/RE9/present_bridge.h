#pragma once
#include "../../src/native_game_submission.h"
#include <d3dcompiler.h>
// Own resources/lists only. Host producer must already be submitted; target starts/ends PRESENT.
class Re9PresentBridge {
 ID3D12Resource *copy{},*color{},*packed{};
 ID3D12DescriptorHeap*heap{};ID3D12RootSignature*root{};ID3D12PipelineState *unpack{},*pack{};
 UINT width{},height{},pitch{},stride{};
 NativeGameSubmission submit;
 static void ck(HRESULT h){if(FAILED(h))throw std::runtime_error("present bridge HRESULT="+std::to_string(unsigned(h)));}
 static void barrier(ID3D12GraphicsCommandList*c,ID3D12Resource*r,D3D12_RESOURCE_STATES a,D3D12_RESOURCE_STATES b){if(a==b)return;D3D12_RESOURCE_BARRIER x{};x.Type=D3D12_RESOURCE_BARRIER_TYPE_TRANSITION;x.Transition={r,D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES,a,b};c->ResourceBarrier(1,&x);}
 void Bind(ID3D12GraphicsCommandList*c,bool output){UINT constants[]={width,height,pitch,0};c->SetDescriptorHeaps(1,&heap);c->SetComputeRootSignature(root);c->SetPipelineState(output?pack:unpack);c->SetComputeRoot32BitConstants(0,4,constants,0);auto h=heap->GetGPUDescriptorHandleForHeapStart();h.ptr+=(output?2:0)*stride;c->SetComputeRootDescriptorTable(1,h);h.ptr+=stride;c->SetComputeRootDescriptorTable(2,h);c->Dispatch((width+15)/16,(height+15)/16,1);}
public:
 ~Re9PresentBridge(){try{submit.Flush();}catch(...){return;}if(copy)copy->Release();if(color)color->Release();if(packed)packed->Release();if(heap)heap->Release();if(root)root->Release();if(pack)pack->Release();if(unpack)unpack->Release();}
 void Create(ID3D12CommandQueue*q,UINT w,UINT h){
  width=w;height=h;pitch=(w*4+255)&~255u;submit.Create(q,false);auto*d=submit.Device();D3D12_HEAP_PROPERTIES hp{};hp.Type=D3D12_HEAP_TYPE_DEFAULT;
  D3D12_RESOURCE_DESC r{};r.Dimension=D3D12_RESOURCE_DIMENSION_TEXTURE2D;r.Width=w;r.Height=h;r.DepthOrArraySize=r.MipLevels=1;r.SampleDesc.Count=1;r.Format=DXGI_FORMAT_R10G10B10A2_UNORM;
  ck(d->CreateCommittedResource(&hp,D3D12_HEAP_FLAG_NONE,&r,D3D12_RESOURCE_STATE_COPY_DEST,nullptr,IID_PPV_ARGS(&copy)));
  r.Format=DXGI_FORMAT_R16G16B16A16_FLOAT;r.Flags=D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS;
  ck(d->CreateCommittedResource(&hp,D3D12_HEAP_FLAG_NONE,&r,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE,nullptr,IID_PPV_ARGS(&color)));
  r={};r.Dimension=D3D12_RESOURCE_DIMENSION_BUFFER;r.Width=UINT64(pitch)*h;r.Height=1;r.DepthOrArraySize=r.MipLevels=1;r.SampleDesc.Count=1;r.Layout=D3D12_TEXTURE_LAYOUT_ROW_MAJOR;r.Flags=D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS;
  ck(d->CreateCommittedResource(&hp,D3D12_HEAP_FLAG_NONE,&r,D3D12_RESOURCE_STATE_COPY_SOURCE,nullptr,IID_PPV_ARGS(&packed)));
  D3D12_DESCRIPTOR_HEAP_DESC hd{D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV,4,D3D12_DESCRIPTOR_HEAP_FLAG_SHADER_VISIBLE,0};ck(d->CreateDescriptorHeap(&hd,IID_PPV_ARGS(&heap)));stride=d->GetDescriptorHandleIncrementSize(hd.Type);auto cpu=heap->GetCPUDescriptorHandleForHeapStart();
  D3D12_SHADER_RESOURCE_VIEW_DESC sv{};sv.ViewDimension=D3D12_SRV_DIMENSION_TEXTURE2D;sv.Shader4ComponentMapping=D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;sv.Texture2D.MipLevels=1;sv.Format=DXGI_FORMAT_R10G10B10A2_UNORM;d->CreateShaderResourceView(copy,&sv,cpu);cpu.ptr+=stride;
  D3D12_UNORDERED_ACCESS_VIEW_DESC uv{};uv.ViewDimension=D3D12_UAV_DIMENSION_TEXTURE2D;uv.Format=DXGI_FORMAT_R16G16B16A16_FLOAT;d->CreateUnorderedAccessView(color,nullptr,&uv,cpu);cpu.ptr+=stride;
  sv.Format=DXGI_FORMAT_R16G16B16A16_FLOAT;d->CreateShaderResourceView(color,&sv,cpu);cpu.ptr+=stride;
  uv={};uv.ViewDimension=D3D12_UAV_DIMENSION_BUFFER;uv.Format=DXGI_FORMAT_R32_TYPELESS;uv.Buffer.NumElements=pitch*h/4;uv.Buffer.Flags=D3D12_BUFFER_UAV_FLAG_RAW;d->CreateUnorderedAccessView(packed,nullptr,&uv,cpu);
  D3D12_DESCRIPTOR_RANGE ranges[2]={{D3D12_DESCRIPTOR_RANGE_TYPE_SRV,1,0,0,0},{D3D12_DESCRIPTOR_RANGE_TYPE_UAV,1,0,0,0}};D3D12_ROOT_PARAMETER params[3]{};params[0].ParameterType=D3D12_ROOT_PARAMETER_TYPE_32BIT_CONSTANTS;params[0].Constants={0,0,4};for(int i=1;i<3;i++){params[i].ParameterType=D3D12_ROOT_PARAMETER_TYPE_DESCRIPTOR_TABLE;params[i].DescriptorTable={1,&ranges[i-1]};}
  D3D12_ROOT_SIGNATURE_DESC rd{};rd.NumParameters=3;rd.pParameters=params;ID3DBlob*b=nullptr,*err=nullptr;auto hr=D3D12SerializeRootSignature(&rd,D3D_ROOT_SIGNATURE_VERSION_1,&b,&err);if(err)err->Release();ck(hr);ck(d->CreateRootSignature(0,b->GetBufferPointer(),b->GetBufferSize(),IID_PPV_ARGS(&root)));b->Release();
  const char*shader=R"(cbuffer C:register(b0){uint2 Size;uint Pitch;uint Pad;}Texture2D<float4> Src:register(t0);
#ifdef PACK
RWByteAddressBuffer Dst:register(u0);
#else
RWTexture2D<float4> Dst:register(u0);
#endif
[numthreads(16,16,1)]void main(uint3 p:SV_DispatchThreadID){if(any(p.xy>=Size))return;float4 v=Src.Load(int3(p.xy,0));
#ifdef PACK
uint4 q=uint4(round(saturate(v)*float4(1023,1023,1023,3)));Dst.Store(p.y*Pitch+p.x*4,q.x|(q.y<<10)|(q.z<<20)|(q.w<<30));
#else
Dst[p.xy]=v;
#endif
})";
  for(int i=0;i<2;i++){D3D_SHADER_MACRO m[]={{"PACK","1"},{nullptr,nullptr}};b=err=nullptr;hr=D3DCompile(shader,strlen(shader),"present-convert",i?m:nullptr,nullptr,"main","cs_5_1",D3DCOMPILE_OPTIMIZATION_LEVEL3,0,&b,&err);if(err)err->Release();ck(hr);D3D12_COMPUTE_PIPELINE_STATE_DESC pd{};pd.pRootSignature=root;pd.CS={b->GetBufferPointer(),b->GetBufferSize()};hr=d->CreateComputePipelineState(&pd,IID_PPV_ARGS(i?&pack:&unpack));b->Release();ck(hr);}
 }
 ID3D12Resource* Color(){return color;}
 bool Matches(ID3D12Resource*r)const{auto d=r->GetDesc();return d.Width==width&&d.Height==height&&d.Format==DXGI_FORMAT_R10G10B10A2_UNORM&&d.SampleDesc.Count==1&&d.MipLevels==1;}
 void Read(ID3D12Resource*back){if(!Matches(back))throw std::runtime_error("present input geometry/format");submit.Submit([&](ID3D12GraphicsCommandList*c){barrier(c,back,D3D12_RESOURCE_STATE_PRESENT,D3D12_RESOURCE_STATE_COPY_SOURCE);c->CopyResource(copy,back);barrier(c,back,D3D12_RESOURCE_STATE_COPY_SOURCE,D3D12_RESOURCE_STATE_PRESENT);barrier(c,copy,D3D12_RESOURCE_STATE_COPY_DEST,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE);barrier(c,color,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE,D3D12_RESOURCE_STATE_UNORDERED_ACCESS);Bind(c,false);barrier(c,color,D3D12_RESOURCE_STATE_UNORDERED_ACCESS,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE);barrier(c,copy,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE,D3D12_RESOURCE_STATE_COPY_DEST);});submit.Flush();}
 void Write(ID3D12Resource*back){if(!Matches(back))throw std::runtime_error("present output geometry/format");submit.Submit([&](ID3D12GraphicsCommandList*c){barrier(c,packed,D3D12_RESOURCE_STATE_COPY_SOURCE,D3D12_RESOURCE_STATE_UNORDERED_ACCESS);Bind(c,true);barrier(c,packed,D3D12_RESOURCE_STATE_UNORDERED_ACCESS,D3D12_RESOURCE_STATE_COPY_SOURCE);barrier(c,back,D3D12_RESOURCE_STATE_PRESENT,D3D12_RESOURCE_STATE_COPY_DEST);D3D12_TEXTURE_COPY_LOCATION a{},b{};a.pResource=back;a.Type=D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX;b.pResource=packed;b.Type=D3D12_TEXTURE_COPY_TYPE_PLACED_FOOTPRINT;b.PlacedFootprint.Footprint={DXGI_FORMAT_R10G10B10A2_UNORM,width,height,1,pitch};c->CopyTextureRegion(&a,0,0,0,&b,nullptr);barrier(c,back,D3D12_RESOURCE_STATE_COPY_DEST,D3D12_RESOURCE_STATE_PRESENT);});submit.Flush();}
};
