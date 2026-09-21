#pragma once
#include <filesystem>
#include <fstream>
#include <vector>
#include <string>
#include <stdexcept>
// Diagnostic only. Copies belong to the existing producer/consumer; readback is
// mapped only after the host acknowledges the consumer and its fence completes.
struct Re9ColourCapture {
 struct Item {ID3D12Resource* readback;D3D12_RESOURCE_DESC desc;D3D12_PLACED_SUBRESOURCE_FOOTPRINT footprint;UINT64 bytes;std::string name;};
 std::vector<Item> items;
 std::filesystem::path directory;
 bool active=false;
 static void Check(HRESULT hr){if(FAILED(hr))throw std::runtime_error("RE9 colour capture D3D12 failure");}
 void Begin(const std::wstring& dll, uint64_t frame, float pre, float scale, ID3D12Resource* exposure){
  if(active||!items.empty())return;
  auto marker=std::filesystem::path(dll)/L"capture-colour.request";
  if(!std::filesystem::exists(marker))return;
  directory=std::filesystem::path(dll)/(L"colour-capture-"+std::to_wstring(GetTickCount64()));
  std::filesystem::create_directories(directory);
  std::filesystem::remove(marker);
  std::ofstream meta(directory/"frame.json");
  meta<<"{\"frame\":"<<frame<<",\"pre_exposure\":"<<pre<<",\"exposure_scale\":"<<scale<<",\"has_exposure\":"<<(exposure?"true":"false")<<"}\n";
  active=true;
 }
 void Record(ID3D12Device* d,ID3D12GraphicsCommandList* c,ID3D12Resource* r,D3D12_RESOURCE_STATES state,const char* name){
  if(!active||!r)return;
  const auto desc=r->GetDesc();
  if(desc.Dimension!=D3D12_RESOURCE_DIMENSION_TEXTURE2D && desc.Dimension!=D3D12_RESOURCE_DIMENSION_BUFFER)return;
  Item item{};item.desc=desc;item.name=name;
  if(desc.Dimension==D3D12_RESOURCE_DIMENSION_TEXTURE2D){
   if(desc.SampleDesc.Count!=1)return;
   d->GetCopyableFootprints(&desc,0,1,0,&item.footprint,nullptr,nullptr,&item.bytes);
  }else item.bytes=desc.Width;
  D3D12_RESOURCE_DESC bd{};bd.Dimension=D3D12_RESOURCE_DIMENSION_BUFFER;bd.Width=item.bytes;bd.Height=1;bd.DepthOrArraySize=bd.MipLevels=1;bd.SampleDesc.Count=1;bd.Layout=D3D12_TEXTURE_LAYOUT_ROW_MAJOR;
  D3D12_HEAP_PROPERTIES hp{};hp.Type=D3D12_HEAP_TYPE_READBACK;
  Check(d->CreateCommittedResource(&hp,D3D12_HEAP_FLAG_NONE,&bd,D3D12_RESOURCE_STATE_COPY_DEST,nullptr,IID_PPV_ARGS(&item.readback)));
  items.push_back(item);
  D3D12_RESOURCE_BARRIER barrier{};barrier.Type=D3D12_RESOURCE_BARRIER_TYPE_TRANSITION;
  barrier.Transition={r,D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES,state,D3D12_RESOURCE_STATE_COPY_SOURCE};
  if(state!=D3D12_RESOURCE_STATE_COPY_SOURCE)c->ResourceBarrier(1,&barrier);
  if(desc.Dimension==D3D12_RESOURCE_DIMENSION_BUFFER)c->CopyBufferRegion(item.readback,0,r,0,item.bytes);
  else {D3D12_TEXTURE_COPY_LOCATION src{},dst{};src.pResource=r;src.Type=D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX;dst.pResource=item.readback;dst.Type=D3D12_TEXTURE_COPY_TYPE_PLACED_FOOTPRINT;dst.PlacedFootprint=item.footprint;c->CopyTextureRegion(&dst,0,0,0,&src,nullptr);}
  std::swap(barrier.Transition.StateBefore,barrier.Transition.StateAfter);
  if(state!=D3D12_RESOURCE_STATE_COPY_SOURCE)c->ResourceBarrier(1,&barrier);
 }
 void DumpAfterCompletion(){
  for(auto& i:items){void* p=nullptr;D3D12_RANGE range{0,SIZE_T(i.bytes)};Check(i.readback->Map(0,&range,&p));
   std::ofstream raw(directory/(i.name+".bin"),std::ios::binary);raw.write((const char*)p,i.bytes);raw.close();
   D3D12_RANGE empty{0,0};i.readback->Unmap(0,&empty);
   std::ofstream meta(directory/(i.name+".json"));meta<<"{\"width\":"<<i.desc.Width<<",\"height\":"<<i.desc.Height<<",\"format\":"<<unsigned(i.desc.Format)<<",\"dimension\":"<<unsigned(i.desc.Dimension)<<",\"row_pitch\":"<<i.footprint.Footprint.RowPitch<<",\"offset\":"<<i.footprint.Offset<<",\"bytes\":"<<i.bytes<<"}\n";
   i.readback->Release();
  }
  items.clear();active=false;
 }
};
