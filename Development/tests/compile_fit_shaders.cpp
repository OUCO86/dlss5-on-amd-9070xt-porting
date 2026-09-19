#include <windows.h>
#include <d3dcompiler.h>
#include <d3d12shader.h>
#include <cstdio>
#include <string>
int wmain(int argc,wchar_t**argv){
 if(argc!=2)return 2;
 unsigned count=0;
 for(const char*fit:{"0","1"})for(const char*srgb:{"0","1"})for(unsigned output=0;output<5;output++){
  D3D_SHADER_MACRO m[]={{"NATIVE_CODEC_FIT",fit},{"NATIVE_CODEC_SRGB_IO",srgb},{"NATIVE_CODEC_UNORM8_OUT",output>=2&&output<4?"1":"0"},{"NATIVE_CODEC_UINT_OUT",output==1?"1":"0"},{"NATIVE_CODEC_BGRA",output==3?"1":"0"},{"NATIVE_CODEC_R11_OUT",output==4?"1":"0"},{nullptr,nullptr}};
  for(const wchar_t*name:{L"native_codec_encode.hlsl",L"native_codec_decode.hlsl"}){
   std::wstring path=std::wstring(argv[1])+L"\\"+name;ID3DBlob*b=nullptr,*e=nullptr;
   HRESULT hr=D3DCompileFromFile(path.c_str(),m,D3D_COMPILE_STANDARD_FILE_INCLUDE,"main","cs_5_1",D3DCOMPILE_OPTIMIZATION_LEVEL3,0,&b,&e);
   if(e){fwrite(e->GetBufferPointer(),1,e->GetBufferSize(),stderr);e->Release();}if(FAILED(hr)){fprintf(stderr,"FAIL fit=%s srgb=%s output=%u shader=%ls hr=%08x\n",fit,srgb,output,name,unsigned(hr));return 1;}if(output==4&&std::wstring(name)==L"native_codec_decode.hlsl"){
    ID3D12ShaderReflection*r=nullptr;D3D12_SHADER_INPUT_BIND_DESC bind{};
    bool valid=SUCCEEDED(D3DReflect(b->GetBufferPointer(),b->GetBufferSize(),IID_ID3D12ShaderReflection,reinterpret_cast<void**>(&r)))&&SUCCEEDED(r->GetResourceBindingDescByName("OutputBits",&bind))&&bind.Type==D3D_SIT_UAV_RWBYTEADDRESS;
    if(r)r->Release();if(!valid){fprintf(stderr,"R11 decode must expose raw OutputBits UAV\n");b->Release();return 1;}
   }b->Release();count++;
  }
 }
 for(const char*viewport:{"0","1"})for(const char*fast:{"0","1"}){
  D3D_SHADER_MACRO m[]={{"NATIVE_INPUT_VIEWPORT",viewport},{"NATIVE_FAST_TEMPORAL",fast},{"NORMALIZED_COORDINATES","1"},{nullptr,nullptr}};
  auto path=std::wstring(argv[1])+L"\\native_temporal_coordinates.hlsl";ID3DBlob*b=nullptr,*e=nullptr;
  auto hr=D3DCompileFromFile(path.c_str(),m,D3D_COMPILE_STANDARD_FILE_INCLUDE,"main","cs_5_1",D3DCOMPILE_OPTIMIZATION_LEVEL3,0,&b,&e);
  if(e){fwrite(e->GetBufferPointer(),1,e->GetBufferSize(),stderr);e->Release();}if(FAILED(hr))return 1;b->Release();count++;
 }
 printf("PASS %u shader variants compiled with production D3DCompiler\n",count);return 0;
}
