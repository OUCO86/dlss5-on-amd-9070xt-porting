"""Skip structurally zero K16 halves in C32 diagonal residual WMMA."""
from pathlib import Path
import hashlib
import json
import shutil

HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[3]; OUT=Path('/tmp/c32-diag-zero')
OUT.mkdir(exist_ok=True)
def rep(s,a,b):
    assert s.count(a)==1,(a[:70],s.count(a))
    return s.replace(a,b,1)
s=(ROOT/'hip/c32_fused_ffn_attention.hip').read_text()
a=s.index('template<bool HalfOutput,bool Mapped=false'); b=s.index('\nKERNEL ',a);body=s[a:b]
old='for(uint part=0;part<3;part++)for(uint ci=0;ci<2;ci++)for(uint kt=0;kt<2;kt++){i2 a=load8(packed+(first+rc())*36+kt*16+gr()*8),b=matrix8(fw,34944+((part*2+ci)*2+kt)*512+(gr()*16+rc())*8);acc[ci]=C32_WMMA_ACC(a,b,acc[ci]);}'
assert body.count(old)==2
new=old.replace('for(uint kt=0;kt<2;kt++){','{const uint kt=ci;')
changed=body.replace(old,new)
code='#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_C32_DIAG_WEIGHTS 1\n'+s
names=['c32_fast_ffn_attention_fused_half_chain','c32_fast_ffn_attention_fused_half_chain_finish_dcrop','c32_fast_ffn_attention_fused_half_chain_finish']
for mode,v in [(1,body),(2,changed)]:
    code+='\n'+v.replace('c32_fused_body(',f'c32_dz{mode}_body(',1)
    for name in names:
        line=next(x for x in s[b:].splitlines() if x.startswith('void '+name+'('))
        line=line.replace('void '+name+'(',f'void {name}_dz{mode}(',1).replace('c32_fused_body<',f'c32_dz{mode}_body<')
        code+='\nKERNEL __attribute__((amdgpu_flat_work_group_size(128,128))) C32_OCC\n'+line+'\n'
code+='''
// 256 logical rows per coefficient cover every finite FP8 value (NaN encodings mapped to +/-448).
KERNEL __attribute__((amdgpu_flat_work_group_size(128,128)))
void c32_diag_zero_check(const float*fw,uint*out){
 uint tid=__builtin_amdgcn_workitem_id_x(),row=bid()*64+(tid/32)*16+rc();
 f8 reference[2]{},candidate[2]{};
 for(uint part=0;part<3;part++)for(uint ci=0;ci<2;ci++)for(uint kt=0;kt<2;kt++){
  i2 a{};for(uint e=0;e<8;e++){uint k=kt*16+gr()*8+e,code=(row+k*17)&255u;if((code&127u)==127u)code--;put_bits(a,e,code);}
  i2 b=matrix8(fw,34944+((part*2+ci)*2+kt)*512+(gr()*16+rc())*8);
  reference[ci]=C32_WMMA_ACC(a,b,reference[ci]);
 }
 for(uint part=0;part<3;part++)for(uint ci=0;ci<2;ci++){
  uint kt=ci;i2 a{};for(uint e=0;e<8;e++){uint k=kt*16+gr()*8+e,code=(row+k*17)&255u;if((code&127u)==127u)code--;put_bits(a,e,code);}
  i2 b=matrix8(fw,34944+((part*2+ci)*2+kt)*512+(gr()*16+rc())*8);
  candidate[ci]=C32_WMMA_ACC(a,b,candidate[ci]);
 }
 uint bad=0;for(uint ci=0;ci<2;ci++)for(uint e=0;e<8;e++)bad+=bits(reference[ci][e])!=bits(candidate[ci][e]);
 out[bid()*128+tid]=bad;
}
'''
(OUT/'kernel.hip').write_text(code)
# Keep every non-target function's machine code identical to the measured baseline.
# A global template edit also changes mode-0 kernels' allocation/scheduling, even
# though their numeric branch is unchanged. Route only the three tested exports.
tail=s[b:]
for name in names:
    line=next(x for x in tail.splitlines() if x.startswith('void '+name+'('))
    tail=rep(tail,line,line.replace('c32_fused_body<','c32_candidate_body<'))
candidate=s[:b]+'\n'+changed.replace('c32_fused_body(','c32_candidate_body(',1)+'\n'+tail
(OUT/'candidate.hip').write_text('#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_C32_DIAG_WEIGHTS 1\n'+candidate)
(OUT/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (ROOT/'Development/HIP').glob('*.h'):shutil.copyfile(p,OUT/'Development/HIP'/p.name)
p=OUT/'Development/HIP/hip_reference_network.h';h=p.read_text()
h=rep(h,'class Network {','class Network {\n unsigned diag_mode=0,diag_calls=0;')
selected='||'.join('original=="'+n+'"' for n in names)
h=rep(h,' Handle Fn(const std::string&m,const std::string&name){',''' Handle Fn(const std::string&m,const std::string&original){
 std::string name=original;
 if(m=="c32_fused_ffn"&&('''+selected+''')){++diag_calls;if(diag_mode)name+="_dz"+std::to_string(diag_mode);}
''')
h=rep(h,' Handle Stream()const{return stream;}', ''' void SetDiagMode(unsigned m){if(m>2)throw std::runtime_error("diag mode");Synchronize();diag_mode=m;diag_calls=0;}
 unsigned DiagCalls()const{return diag_calls;}
 void CheckDiagFinite(){
  void*output=nullptr;api.Check(api.hipMalloc(&output,512*4),"diag check alloc");
  for(unsigned block:{2u,3u,4u,67u,68u,69u}){
   Run("c32_fused_ffn","c32_diag_zero_check",4,PackedC32Weight(Block(block,"ffn"),false),output);
   Synchronize();std::vector<unsigned>bad(512);api.Check(api.hipMemcpy(bad.data(),output,512*4,2),"diag check read");
   unsigned total=0;for(auto n:bad)total+=n;printf("FINITE block=%u comparisons=8192 bitdiff=%u\\n",block,total);fflush(stdout);
   if(total)throw std::runtime_error("finite FP8 diagonal mismatch");
  }
  api.Check(api.hipFree(output),"diag check free");
 }
 Handle Stream()const{return stream;}''')
p.write_text(h)
native=(ROOT/'src/native_hip_network.h').read_text();a=native.index('hip_reference::Options o;');b=native.index('  const wchar_t*modules=',a)
opts=native[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift','o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)','o.assets=argv[1]')
runner=(HERE.parent/'c32-post-input/runner.cpp.in').read_text()
runner=runner.replace('SetPostMode','SetDiagMode').replace('PostCalls','DiagCalls').replace('post_calls','diag_calls').replace('POST_INPUT_CANDIDATES','C32_DIAG_CANDIDATES')
runner=runner.replace('candidates{1u,2u,3u,4u}','candidates{1u,2u}').replace('m>4','m>2').replace('candidate must be 1..4','candidate must be 1..2').replace('calls!=frames','calls!=frames*6').replace('post must execute exactly once per frame','expected six diagonal C32 calls per frame').replace('PASS post input controls','PASS C32 diagonal zero controls')
runner=rep(runner,'auto&api=net.Runtime();','auto&api=net.Runtime();net.CheckDiagFinite();')
(OUT/'network.cpp').write_text(runner.replace('/* OPTIONS */',opts))
for name in ('build.ps1','run.ps1','start.ps1','build-candidate.ps1','regression.ps1','qualify.ps1','collect.ps1'):shutil.copyfile(HERE/name,OUT/name)
(OUT/'source-manifest.json').write_text(json.dumps({'source_sha256':hashlib.sha256(s.encode()).hexdigest(),'modes':{'0':'production','1':'identical control','2':'skip zero K16 diagonal halves'}},indent=2)+'\n')
print(OUT)
