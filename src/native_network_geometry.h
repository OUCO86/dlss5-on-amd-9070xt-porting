#pragma once
#include <cstdlib>
#include <cwchar>
#include <stdexcept>

struct NativeNetworkGeometry {
 unsigned valid_width,valid_height,processing_width,processing_height;
 static NativeNetworkGeometry FromHeight(unsigned height){
  if(height==720)return {1280,720,1280,768};
  if(height==1080)return {1920,1080,1920,1152};
  throw std::runtime_error("unsupported network height");
 }
};
inline NativeNetworkGeometry NativeCurrentNetworkGeometry(){
#ifdef _WIN32
 const wchar_t*value=_wgetenv(L"DLSS5_NETWORK_720P");
 if(value&&wcscmp(value,L"0")&&wcscmp(value,L"1"))throw std::runtime_error("invalid DLSS5_NETWORK_720P flag");
 return NativeNetworkGeometry::FromHeight(value&&!wcscmp(value,L"1")?720:1080);
#else
 const char*value=std::getenv("DLSS5_NETWORK_720P");
 if(value&&!(value[0]=='0'&&!value[1])&&!(value[0]=='1'&&!value[1]))throw std::runtime_error("invalid DLSS5_NETWORK_720P flag");
 return NativeNetworkGeometry::FromHeight(value&&value[0]=='1'?720:1080);
#endif
}
