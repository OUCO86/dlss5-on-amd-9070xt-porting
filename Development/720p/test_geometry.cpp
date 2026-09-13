#include "../../src/native_network_geometry.h"
#include "../../src/native_input_geometry.h"
#include <cassert>
#include <cstdio>
int main(){
 for(unsigned h:{720u,900u,1080u}){
  auto n=NativeNetworkGeometry::FromHeight(h);
  assert(n.processing_width==n.valid_width&&n.processing_height%128==0&&n.processing_height>=h);
  for(auto wh:{std::pair<unsigned,unsigned>{1920,1080},{1914,1063},{1280,720},{1600,900},{1440,1080},{640,480},{1,1},{1,1080},{1920,1}}){
   auto g=NativeInputGeometry::Make(wh.first,wh.second,n.valid_width,n.valid_height);
   assert(g.network_width==n.valid_width&&g.network_height==n.valid_height);
   assert(g.x+g.fit_width<=n.valid_width&&g.y+g.fit_height<=n.valid_height);
   assert(g.fit_width==n.valid_width||g.fit_height==n.valid_height);
  }
 }
 auto g=NativeInputGeometry::Make(1920,1080,1280,720);assert(g.x==0&&g.y==0&&g.fit_width==1280&&g.fit_height==720&&g.Adapted());
 auto v=NativeInputGeometry::Make(1920,1080,1600,900);assert(v.x==0&&v.y==0&&v.fit_width==1600&&v.fit_height==900);
 assert(NativeNetworkGeometry::FromHeight(900).VitTokens()==400);
 setenv("DLSS5_NETWORK_720P","1",1);setenv("DLSS5_NETWORK_HEIGHT","900",1);assert(NativeCurrentNetworkGeometry().valid_height==900);
 unsetenv("DLSS5_NETWORK_HEIGHT");assert(NativeCurrentNetworkGeometry().valid_height==720);unsetenv("DLSS5_NETWORK_720P");assert(NativeCurrentNetworkGeometry().valid_height==1080);
 puts("720p/900p/1080p network geometry and external-input viewports PASS");
}
