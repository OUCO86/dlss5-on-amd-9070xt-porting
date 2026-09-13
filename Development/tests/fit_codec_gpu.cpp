// Usage: fit_codec_gpu.exe <shader-directory> [vendor-hex, default 1002]
// Codec only: no model, weights, game hooks or persisted configuration.
#include <windows.h>
#include <dxgi1_6.h>
#include <d3d12.h>
#include <d3dcompiler.h>
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <vector>
#include <string>
#include <stdexcept>
#include "../../src/native_game_codec.h"
#include "../../src/native_game_submission.h"
static void ck(HRESULT h){if(FAILED(h))throw std::runtime_error("HRESULT="+std::to_string(unsigned(h)));}
static void need(bool b,const char*s){if(!b)throw std::runtime_error(s);}
struct Resources {std::vector<ID3D12Resource*> items;~Resources(){for(auto*p:items)p->Release();}
 ID3D12Resource* make(ID3D12Device*d,D3D12_RESOURCE_DESC desc,D3D12_HEAP_TYPE type,D3D12_RESOURCE_STATES state){D3D12_HEAP_PROPERTIES hp{};hp.Type=type;ID3D12Resource*r=nullptr;ck(d->CreateCommittedResource(&hp,D3D12_HEAP_FLAG_NONE,&desc,state,nullptr,IID_PPV_ARGS(&r)));items.push_back(r);return r;}
 ID3D12Resource* buffer(ID3D12Device*d,UINT64 n,D3D12_HEAP_TYPE t,D3D12_RESOURCE_STATES s){D3D12_RESOURCE_DESC desc{};desc.Dimension=D3D12_RESOURCE_DIMENSION_BUFFER;desc.Width=n;desc.Height=1;desc.DepthOrArraySize=desc.MipLevels=1;desc.SampleDesc.Count=1;desc.Layout=D3D12_TEXTURE_LAYOUT_ROW_MAJOR;return make(d,desc,t,s);}
};
static void barrier(ID3D12GraphicsCommandList*c,ID3D12Resource*r,D3D12_RESOURCE_STATES a,D3D12_RESOURCE_STATES b){if(a==b)return;D3D12_RESOURCE_BARRIER v{};v.Type=D3D12_RESOURCE_BARRIER_TYPE_TRANSITION;v.Transition={r,D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES,a,b};c->ResourceBarrier(1,&v);}
static D3D12_TEXTURE_COPY_LOCATION tex(ID3D12Resource*r){D3D12_TEXTURE_COPY_LOCATION x{};x.pResource=r;x.Type=D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX;return x;}
static D3D12_TEXTURE_COPY_LOCATION placed(ID3D12Resource*r,D3D12_PLACED_SUBRESOURCE_FOOTPRINT f){D3D12_TEXTURE_COPY_LOCATION x{};x.pResource=r;x.Type=D3D12_TEXTURE_COPY_TYPE_PLACED_FOOTPRINT;x.PlacedFootprint=f;return x;}
static unsigned char sample(unsigned x,unsigned y,unsigned c,unsigned w,unsigned h){return c==0?(x*255/std::max(1u,w-1)):c==1?(y*255/std::max(1u,h-1)):c==2?((x+3*y)%256):((x+y)%256);}
static float half(uint16_t h){unsigned e=(h>>10)&31,m=h&1023;float f=e?std::ldexp(float(1024+m),int(e)-25):std::ldexp(float(m),-24);return h&32768?-f:f;}
static void test(ID3D12Device*d,NativeGameSubmission&submit,const std::wstring&dir,unsigned w,unsigned h){
 Resources resources;
 D3D12_RESOURCE_DESC td{};td.Dimension=D3D12_RESOURCE_DIMENSION_TEXTURE2D;td.Width=w;td.Height=h;td.DepthOrArraySize=td.MipLevels=1;td.Format=DXGI_FORMAT_R8G8B8A8_UNORM;td.SampleDesc.Count=1;
 auto*original=resources.make(d,td,D3D12_HEAP_TYPE_DEFAULT,D3D12_RESOURCE_STATE_COPY_DEST);
 auto*result=resources.make(d,td,D3D12_HEAP_TYPE_DEFAULT,D3D12_RESOURCE_STATE_COPY_DEST);
 D3D12_PLACED_SUBRESOURCE_FOOTPRINT fp{};UINT64 bytes{};d->GetCopyableFootprints(&td,0,1,0,&fp,nullptr,nullptr,&bytes);
 auto*upload=resources.buffer(d,bytes,D3D12_HEAP_TYPE_UPLOAD,D3D12_RESOURCE_STATE_GENERIC_READ);
 auto*rb=resources.buffer(d,bytes,D3D12_HEAP_TYPE_READBACK,D3D12_RESOURCE_STATE_COPY_DEST);
 void*m=nullptr;D3D12_RANGE none{};ck(upload->Map(0,&none,&m));std::memset(m,0xCD,size_t(bytes));
 for(unsigned y=0;y<h;y++)for(unsigned x=0;x<w;x++)for(unsigned c=0;c<4;c++)static_cast<unsigned char*>(m)[y*fp.Footprint.RowPitch+x*4+c]=sample(x,y,c,w,h);upload->Unmap(0,nullptr);
 NativeGameCodec encoder;encoder.Create(d,{original},dir);
 auto nt=encoder.Output()->GetDesc();nt.Flags=D3D12_RESOURCE_FLAG_NONE;
 auto*neural=resources.make(d,nt,D3D12_HEAP_TYPE_DEFAULT,D3D12_RESOURCE_STATE_COPY_DEST);
 D3D12_PLACED_SUBRESOURCE_FOOTPRINT nfp{};UINT64 nbytes{};d->GetCopyableFootprints(&nt,0,1,0,&nfp,nullptr,nullptr,&nbytes);
 auto*nrb=resources.buffer(d,nbytes,D3D12_HEAP_TYPE_READBACK,D3D12_RESOURCE_STATE_COPY_DEST);
 NativeGameCodec decoder;decoder.Create(d,{encoder.Output(),neural,original},dir);
 need(decoder.BufferOutput(),"expected raw UNORM8 decoder");const auto outfp=decoder.BufferFootprint();
 need(outfp.Width==w&&outfp.Height==h&&outfp.RowPitch==fp.Footprint.RowPitch,"decoder footprint mismatch");
 const UINT64 rawbytes=decoder.Output()->GetDesc().Width;
 need(rawbytes==UINT64(outfp.RowPitch)*h,"raw output allocation extent");
 auto*rawrb=resources.buffer(d,rawbytes,D3D12_HEAP_TYPE_READBACK,D3D12_RESOURCE_STATE_COPY_DEST);
 auto*sentinel=resources.buffer(d,rawbytes,D3D12_HEAP_TYPE_UPLOAD,D3D12_RESOURCE_STATE_GENERIC_READ);
 ck(sentinel->Map(0,&none,&m));std::memset(m,0xCD,size_t(rawbytes));sentinel->Unmap(0,nullptr);
 submit.Submit([&](ID3D12GraphicsCommandList*c){
  auto src=placed(upload,fp),dst=tex(original);c->CopyTextureRegion(&dst,0,0,0,&src,nullptr);
  barrier(c,original,D3D12_RESOURCE_STATE_COPY_DEST,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE);
  encoder.Record(c,{D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE},1.f);
  barrier(c,encoder.Output(),D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE,D3D12_RESOURCE_STATE_COPY_SOURCE);
  c->CopyResource(neural,encoder.Output());src=tex(encoder.Output());dst=placed(nrb,nfp);c->CopyTextureRegion(&dst,0,0,0,&src,nullptr);
  barrier(c,encoder.Output(),D3D12_RESOURCE_STATE_COPY_SOURCE,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE);
  barrier(c,neural,D3D12_RESOURCE_STATE_COPY_DEST,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE);
  barrier(c,decoder.Output(),D3D12_RESOURCE_STATE_UNORDERED_ACCESS,D3D12_RESOURCE_STATE_COPY_DEST);c->CopyBufferRegion(decoder.Output(),0,sentinel,0,rawbytes);
  barrier(c,decoder.Output(),D3D12_RESOURCE_STATE_COPY_DEST,D3D12_RESOURCE_STATE_UNORDERED_ACCESS);
  decoder.Record(c,{D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE},1.f);
  barrier(c,decoder.Output(),D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE,D3D12_RESOURCE_STATE_COPY_SOURCE);
  c->CopyBufferRegion(rawrb,0,decoder.Output(),0,rawbytes);
  D3D12_PLACED_SUBRESOURCE_FOOTPRINT dfp{};dfp.Footprint=outfp;src=placed(decoder.Output(),dfp);dst=tex(result);c->CopyTextureRegion(&dst,0,0,0,&src,nullptr);
  barrier(c,result,D3D12_RESOURCE_STATE_COPY_DEST,D3D12_RESOURCE_STATE_COPY_SOURCE);src=tex(result);dst=placed(rb,fp);c->CopyTextureRegion(&dst,0,0,0,&src,nullptr);
 });
 D3D12_RANGE rr{0,SIZE_T(bytes)};ck(rb->Map(0,&rr,&m));unsigned maxerror=0;size_t changed=0;
 for(unsigned y=0;y<h;y++)for(unsigned x=0;x<w;x++)for(unsigned c=0;c<4;c++){int got=static_cast<unsigned char*>(m)[y*fp.Footprint.RowPitch+x*4+c];unsigned err=unsigned(std::abs(got-int(sample(x,y,c,w,h))));maxerror=std::max(maxerror,err);changed+=err!=0;}
 rb->Unmap(0,&none);need(maxerror<=1,"decode identity differs by more than 1 LSB");
 rr={0,SIZE_T(rawbytes)};ck(rawrb->Map(0,&rr,&m));size_t padding_corruption=0;
 for(unsigned y=0;y<h;y++)for(unsigned x=w*4;x<outfp.RowPitch;x++)padding_corruption+=static_cast<unsigned char*>(m)[y*outfp.RowPitch+x]!=0xCD;
 rawrb->Unmap(0,&none);need(!padding_corruption,"decoder wrote into row padding");
 auto g=NativeInputGeometry::Make(w,h);rr={0,SIZE_T(nbytes)};ck(nrb->Map(0,&rr,&m));float maxfit=0;size_t blackbad=0;
 auto value=[&](unsigned x,unsigned y,unsigned c){uint16_t bits;std::memcpy(&bits,static_cast<unsigned char*>(m)+y*nfp.Footprint.RowPitch+x*8+c*2,2);return half(bits);};
 for(unsigned y=0;y<1080;y++)for(unsigned x=0;x<1920;x++){
  if(x<g.x||x>=g.x+g.fit_width||y<g.y||y>=g.y+g.fit_height){for(unsigned c=0;c<3;c++)blackbad+=value(x,y,c)!=0;blackbad+=value(x,y,3)!=1;continue;}
  float sx=std::clamp((float(x)+.5f-g.x)*w/g.fit_width-.5f,0.f,float(w-1));float sy=std::clamp((float(y)+.5f-g.y)*h/g.fit_height-.5f,0.f,float(h-1));
  unsigned x0=unsigned(sx),y0=unsigned(sy),x1=std::min(x0+1,w-1),y1=std::min(y0+1,h-1);float fx=sx-x0,fy=sy-y0;
  for(unsigned c=0;c<3;c++){float a=sample(x0,y0,c,w,h)*(1-fx)+sample(x1,y0,c,w,h)*fx;float b=sample(x0,y1,c,w,h)*(1-fx)+sample(x1,y1,c,w,h)*fx;float expected=(a*(1-fy)+b*fy)/255.f;maxfit=std::max(maxfit,std::abs(value(x,y,c)-expected));}
 }
 nrb->Unmap(0,&none);need(!blackbad,"encode letterbox not black/opaque");need(maxfit<.001f,"encode bilinear mapping differs");
 std::printf("PASS %ux%u pitch=%u decode_max_lsb=%u changed=%zu encode_max_error=%g padding_intact=1\n",w,h,outfp.RowPitch,maxerror,changed,maxfit);std::fflush(stdout);
}
int wmain(int argc,wchar_t**argv){try{
 if(argc<2||argc>3){std::fprintf(stderr,"usage: fit_codec_gpu.exe shader-directory [vendor-hex]\n");return 2;}
 _wputenv(L"DLSS5_CODEC_SRGB=1");_wputenv(L"DLSS5_STRENGTH=0,0");_wputenv(L"DLSS5_DEBUG_TINT=0");
 IDXGIFactory1*f=nullptr;ck(CreateDXGIFactory1(IID_PPV_ARGS(&f)));ID3D12Device*d=nullptr;unsigned vendor=argc==3?wcstoul(argv[2],nullptr,16):0x1002;
 for(UINT i=0;;i++){IDXGIAdapter1*a=nullptr;if(f->EnumAdapters1(i,&a)==DXGI_ERROR_NOT_FOUND)break;DXGI_ADAPTER_DESC1 desc{};a->GetDesc1(&desc);if(desc.VendorId==vendor)D3D12CreateDevice(a,D3D_FEATURE_LEVEL_12_0,IID_PPV_ARGS(&d));a->Release();if(d)break;}f->Release();need(d!=nullptr,"adapter missing");
 ID3D12CommandQueue*q=nullptr;D3D12_COMMAND_QUEUE_DESC qd{};ck(d->CreateCommandQueue(&qd,IID_PPV_ARGS(&q)));
 {NativeGameSubmission submit;submit.Create(q,false);for(auto s:{std::pair<unsigned,unsigned>{1914,1063},{1280,720},{1440,1080},{641,479},{1920,1080}})test(d,submit,argv[1],s.first,s.second);}
 q->Release();d->Release();return 0;
 }catch(const std::exception&e){std::fprintf(stderr,"FAIL: %s\n",e.what());return 1;}}
