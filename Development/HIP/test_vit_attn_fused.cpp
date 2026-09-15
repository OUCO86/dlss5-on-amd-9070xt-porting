// Bit-exactness of vit_attention_fused against the three-kernel path (scores_fast / inverse_fast / av_fast).
// Synthetic normalized Q/K/V on the E4M3 lattice (what vit_qkv_project_normalize_fused_* emits), three token counts
// (720p 240, 900p 400, 1080p 640) and two value patterns. Compares the attention output bytes; any difference fails.
#define DLSS5_LAYER_BENCH 1
#include "hip_reference_network.h"
#include <cmath>
#include <cstring>
static float fp8(unsigned b){unsigned e=(b>>3)&15,m=b&7;float x=e?std::ldexp(1.f+m/8.f,int(e)-7):m/512.f;return b&128?-x:x;}
namespace hip_reference { struct LayerBenchmark { static bool Check(Network&n){bool ok=true;
 for(unsigned tokens:{240u,400u,640u})for(unsigned pattern=0;pattern<2;pattern++){
  std::vector<float>v(size_t(3)*tokens*1024);
  for(size_t i=0;i<v.size();i++){unsigned code=pattern?unsigned((i*53+i/31+11)%96):unsigned((i*37+i/17+5)%80);if(i%3==0)code|=128;v[i]=fp8(code);}
  auto in=n.Upload(v.data(),v.size()*4);
  auto ex=n.New(size_t(tokens)*32*tokens),inv=n.New(size_t(tokens)*32),a=n.New(size_t(tokens)*1024),b=n.New(size_t(tokens)*1024);
  n.Run("deep","vit_attention_scores_fast",size_t(tokens)*32*tokens,n.P(in),n.P(ex),tokens);
  n.Run("deep","vit_attention_inverse_fast",size_t(tokens)*32,n.P(ex),n.P(inv),tokens);
  n.Run("deep","vit_attention_av_fast",size_t(tokens)*1024,n.P(in),n.P(ex),n.P(inv),n.P(a),tokens);
  n.Run("deep",tokens<=256?"vit_attention_fused_256":tokens<=400?"vit_attention_fused_400":"vit_attention_fused_640",size_t(tokens)*512,n.P(in),n.P(b),tokens);n.Synchronize();
  std::vector<float>x(size_t(tokens)*1024),y(x.size());
  n.api.Check(n.api.hipMemcpy(x.data(),n.P(a),x.size()*4,2),"read reference");n.api.Check(n.api.hipMemcpy(y.data(),n.P(b),y.size()*4,2),"read fused");
  size_t diff=0,bad=0;float maxabs=0;for(size_t i=0;i<x.size();i++){diff+=memcmp(&x[i],&y[i],4)!=0;bad+=!std::isfinite(x[i])||!std::isfinite(y[i]);maxabs=std::fmax(maxabs,std::fabs(x[i]-y[i]));}
  printf("tokens=%u pattern=%u bitdiff=%zu invalid=%zu maxabs=%.9g\n",tokens,pattern,diff,bad,maxabs);ok=ok&&!diff&&!bad;
 }
 return ok;}}; }
int main(int argc,char**argv){try{
 if(argc!=3)throw std::runtime_error("test_vit_attn_fused ASSETS MODULES");
 hip_reference::Options o;o.assets=argv[1];o.modules=argv[2];o.fast_deep=o.fast_vit=o.packed_weights=true;
 hip_reference::Network n(o);bool ok=hip_reference::LayerBenchmark::Check(n);
 printf(ok?"fused attention matches\n":"fused attention MISMATCH\n");return ok?0:1;
}catch(const std::exception&e){fprintf(stderr,"%s\n",e.what());return 1;}}
