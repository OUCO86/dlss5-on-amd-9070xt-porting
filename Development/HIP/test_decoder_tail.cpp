#define DLSS5_LAYER_BENCH 1
#include "hip_reference_network.h"
#include <limits>
namespace hip_reference {
struct LayerBenchmark {
 static void Check(Network&n,U iw,U ih,U ic,U oc,bool crop,unsigned mode,bool legacy=false){
  U ow=iw*2-(crop?1:0),oh=ih*2-(crop?1:0),tokens=iw*ih;size_t size=size_t(ow)*oh*oc;
  std::vector<float>input(size_t(tokens+16)*ic,std::numeric_limits<float>::quiet_NaN()),weights(size_t(ic)*oc+oc,0),skip(size,0),out(size+64,-999.f);
  for(U p=0;p<tokens;p++)for(U c=0;c<ic;c++)input[size_t(p)*ic+c]=float(int((p+c)%7)-3)*.125f;
  for(U c=0;c<oc;c++)weights[size_t(c)*ic+c]=1;
  auto in=n.Upload(input.data(),input.size()*4),w=n.Upload(weights.data(),weights.size()*4),sk=n.Upload(skip.data(),skip.size()*4),dest=n.Upload(out.data(),out.size()*4);
  std::vector<unsigned char>packed(weights.size()*4,0);const unsigned short one=0x3c00;for(U c=0;c<oc;c++)memcpy(packed.data()+2*(size_t(c)*ic+c),&one,2);auto hw=n.Upload(packed.data(),packed.size());
  n.opt.fast_deep=mode!=2;
  if(legacy){void*pi=n.P(in),*pw=n.P(w),*ps=n.P(sk),*po=n.P(dest);void*args[]={&pi,&pw,&ps,&po,&iw,&ih,&ow,&oh,&ic,&oc};n.api.Check(n.api.hipModuleLaunchKernel(n.Fn("deep_fast","decoder_project2x"),(tokens*oc+255)/256,1,1,32,1,1,0,n.stream,args,nullptr),"legacy launch");}
  else n.Run("deep",mode==1?"decoder_project2x_h16w":"decoder_project2x",size_t(tokens)*oc,n.P(in),mode==1?n.P(hw):n.P(w),n.P(sk),n.P(dest),iw,ih,ow,oh,ic,oc);n.Synchronize();
  n.api.Check(n.api.hipMemcpy(out.data(),n.P(dest),out.size()*4,2),"read output");size_t bad=0,unwritten=0,guard=0;
  for(U y=0;y<oh;y++)for(U x=0;x<ow;x++)for(U c=0;c<oc;c++){size_t i=(size_t(y)*ow+x)*oc+c;float expected=input[(size_t(y/2)*iw+x/2)*ic+c];bad+=out[i]!=expected;unwritten+=out[i]==-999.f;}
  for(size_t i=size;i<out.size();i++)guard+=out[i]!=-999.f;
  printf("iw=%u ih=%u ic=%u oc=%u crop=%u mode=%u bad=%zu unwritten=%zu guard=%zu\n",iw,ih,ic,oc,crop,mode,bad,unwritten,guard);
  if(bad||guard)throw std::runtime_error("decoder output coverage/value mismatch");
 }
};
}
int main(int argc,char**argv){try{
 if(argc!=3&&argc!=4)throw std::runtime_error("usage: test_decoder_tail ASSETS MODULES");hip_reference::Options o;o.assets=argv[1];o.modules=argv[2];o.pooled=o.wmma=o.fast_deep=o.packed_weights=true;hip_reference::Network n(o);
 if(argc==4){if(strcmp(argv[3],"legacy"))throw std::runtime_error("unknown mode");hip_reference::LayerBenchmark::Check(n,50,30,512,256,false,0,true);return 2;}
 for(unsigned mode=0;mode<3;mode++){hip_reference::LayerBenchmark::Check(n,50,30,512,256,false,mode);for(bool crop:{false,true}){hip_reference::LayerBenchmark::Check(n,5,3,32,32,crop,mode);hip_reference::LayerBenchmark::Check(n,4,4,32,32,crop,mode);hip_reference::LayerBenchmark::Check(n,17,1,32,32,crop,mode);}}
 puts("DECODER_TAIL_PASS");return 0;
}catch(const std::exception&e){fprintf(stderr,"FAIL %s\n",e.what());return 1;}}
