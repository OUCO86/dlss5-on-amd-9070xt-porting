from pathlib import Path
import difflib,sys,subprocess
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent;vertical='--vertical' in sys.argv;out=Path('/tmp/c128-empty-vertical' if vertical else '/tmp/c128-empty-tile');out.mkdir(exist_ok=True)
s=subprocess.check_output(['git','show','79c1654:hip/multihead_fast_padded.hip'],cwd=root,text=True);a=s.index('DEV void mh_ffn_qkv_body');b=s.index('\nKERNEL ',a)
body=s[a:b];needle=' if(first>=tokens)return;';assert body.count(needle)==1
insert='''
 // The mapped input is identically zero outside its valid rectangle; all weight
 // transforms are bias-free, and q8 canonicalizes signed zero. Skip a wholly
 // empty16-row tile, writing both complete outputs without entering LDS/barriers.
 if constexpr(C==128&&Mapped){
  if(workw>=16){
   uint y=first/workw,x=first%workw,n0=workw-x;if(n0>16)n0=16;
   bool valid0=y>=sy&&y-sy<height&&x<sx+width&&x+n0>sx;
   uint n1=16-n0;bool valid1=n1&&y+1>=sy&&y+1-sy<height&&n1>sx;
   if(!valid0&&!valid1){
    for(uint i=tid;i<16*C;i+=2*C){if constexpr(ByteFeature)out[first*C+i]=0;else reinterpret_cast<float*>(out)[first*C+i]=0.f;}
    for(uint i=tid;i<16*3*C;i+=2*C)norm[first*3*C+i]=0;
    return;
   }
  }
 }
'''
if vertical:
 insert='''
 // A complete16-row tile in top/bottom mapped padding has exactly zero
 // bias-free FFN and normalized QKV outputs. The test is workgroup-uniform.
 if constexpr(C==128&&Mapped){
  if(first+15<sy*workw||first>=(sy+height)*workw){
   for(uint i=tid;i<16*C;i+=2*C){if constexpr(ByteFeature)out[first*C+i]=0;else reinterpret_cast<float*>(out)[first*C+i]=0.f;}
   for(uint i=tid;i<16*3*C;i+=2*C)norm[first*3*C+i]=0;
   return;
  }
 }
'''
t=s[:a]+body.replace(needle,needle+insert,1)+s[b:]
(out/'kernel.hip').write_text('#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_FFN_HOIST_RES 2\n'+t)
(here/('vertical.patch' if vertical else 'candidate.patch')).write_text(''.join(difflib.unified_diff(s.splitlines(True),t.splitlines(True),fromfile='a/hip/multihead_fast_padded.hip',tofile='b/hip/multihead_fast_padded.hip')))
