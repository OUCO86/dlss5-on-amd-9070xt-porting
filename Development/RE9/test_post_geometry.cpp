#define DLSS5_RE9_POST_1440
#include "../../src/native_input_geometry.h"
#include <cassert>
#include <iostream>
int main(){
 for(auto wh:{std::pair<unsigned,unsigned>{2560,1440},{2554,1401},{1920,1080},{1600,900}}){
 auto g=NativeInputGeometry::Make(wh.first,wh.second,1600,900);
 assert(g.width==wh.first&&g.height==wh.second);
 assert(g.network_width==1600&&g.network_height==900);
 assert(g.x+g.fit_width<=1600&&g.y+g.fit_height<=900);
 assert(g.RowPitch(8)>=wh.first*8&&g.RowPitch(8)%256==0);
 }
 auto g=NativeInputGeometry::Make(2560,1440,1600,900);
 assert(g.x==0&&g.y==0&&g.fit_width==1600&&g.fit_height==900);
 for(auto wh:{std::pair<unsigned,unsigned>{0,1440},{2560,0},{2561,1440},{2560,1441},{3840,2160}})assert(!NativeInputGeometry::Supported(wh.first,wh.second));
 std::cout<<"PASS RE9 1440 output / 900 neural viewport\n";
}
