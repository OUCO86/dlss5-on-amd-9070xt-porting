#pragma once
#include <cstdlib>
#include <cwchar>
#include <cstring>
#include <stdexcept>

struct NativeNetworkGeometry {
 unsigned valid_width,valid_height,processing_width,processing_height;
 unsigned VitTokens()const{return valid_height==720?240u:valid_height==900?400u:640u;}
 static NativeNetworkGeometry FromHeight(unsigned height){
  if(height==720)return {1280,720,1280,768};
  if(height==900)return {1600,900,1600,1024};
  if(height==1080)return {1920,1080,1920,1152};
  throw std::runtime_error("unsupported network height");
 }
};
inline NativeNetworkGeometry NativeCurrentNetworkGeometry(){
#ifdef _WIN32
 if(const wchar_t*height=_wgetenv(L"DLSS5_NETWORK_HEIGHT")){
  if(!wcscmp(height,L"720"))return NativeNetworkGeometry::FromHeight(720);
  if(!wcscmp(height,L"900"))return NativeNetworkGeometry::FromHeight(900);
  if(!wcscmp(height,L"1080"))return NativeNetworkGeometry::FromHeight(1080);
  throw std::runtime_error("DLSS5_NETWORK_HEIGHT must be 720, 900 or 1080");
 }
 const wchar_t*value=_wgetenv(L"DLSS5_NETWORK_720P");
 if(value&&wcscmp(value,L"0")&&wcscmp(value,L"1"))throw std::runtime_error("invalid DLSS5_NETWORK_720P flag");
 return NativeNetworkGeometry::FromHeight(value&&!wcscmp(value,L"1")?720:1080);
#else
 if(const char*height=std::getenv("DLSS5_NETWORK_HEIGHT")){
  if(!std::strcmp(height,"720"))return NativeNetworkGeometry::FromHeight(720);
  if(!std::strcmp(height,"900"))return NativeNetworkGeometry::FromHeight(900);
  if(!std::strcmp(height,"1080"))return NativeNetworkGeometry::FromHeight(1080);
  throw std::runtime_error("DLSS5_NETWORK_HEIGHT must be 720, 900 or 1080");
 }
 const char*value=std::getenv("DLSS5_NETWORK_720P");
 if(value&&!(value[0]=='0'&&!value[1])&&!(value[0]=='1'&&!value[1]))throw std::runtime_error("invalid DLSS5_NETWORK_720P flag");
 return NativeNetworkGeometry::FromHeight(value&&value[0]=='1'?720:1080);
#endif
}
