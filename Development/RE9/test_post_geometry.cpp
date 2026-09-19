#include "../../src/native_input_geometry.h"
#include <cassert>
#include <iostream>
int main(){
 auto g=NativeInputGeometry::Make(1920,1080,1600,900);
 assert(g.width==1920&&g.height==1080&&g.fit_width==1600&&g.fit_height==900);
 for(auto wh:{std::pair<unsigned,unsigned>{0,1080},{1920,0},{1921,1080},{1920,1081},{2560,1440},{3840,2160}})assert(!NativeInputGeometry::Supported(wh.first,wh.second));
 std::cout<<"PASS RE9 max1080 output / 900 neural viewport\n";
}
