"""Build an independent two-wave C64 prototype against the current host/production modules."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];OUT=Path('/tmp/c64-wave2');OUT.mkdir(exist_ok=True)
def rep(s,a,b):
 assert s.count(a)==1,(a[:100],s.count(a))
 return s.replace(a,b,1)
base=(ROOT/'hip/multihead_fast_padded.hip').read_text()
kernel='#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_FFN_HOIST_RES 2\n#define HIP_PDL_KERNELS 0\n'+base+'\n'+(HERE/'kernel.inc').read_text()
(OUT/'kernel.hip').write_text(kernel)
(OUT/'kernel-frag.hip').write_text('#define W2_FRAGMENT_WEIGHTS 1\n'+kernel)
(OUT/'kernel-defer.hip').write_text('#define W2_DEFER_Q 1\n'+kernel)
(OUT/'kernel-frag-defer.hip').write_text('#define W2_FRAGMENT_WEIGHTS 1\n#define W2_DEFER_Q 1\n'+kernel)
(OUT/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (ROOT/'Development/HIP').glob('*.h'):shutil.copyfile(p,OUT/'Development/HIP'/p.name)
p=OUT/'Development/HIP/hip_reference_network.h';s=p.read_text()
s=rep(s,'class Network {','class Network {\n unsigned w2_mode=0,w2_calls=0,w2_replaced=0;bool w2_frag=std::getenv("W2_FRAG")&&std::string(std::getenv("W2_FRAG"))=="1";')
s=rep(s,' Handle Stream()const{return stream;}',''' void W2Mode(unsigned mode){if(mode>5)throw std::runtime_error("w2 mode");Synchronize();w2_mode=mode;w2_calls=0;w2_replaced=0;}
 unsigned W2Calls()const{return w2_calls;}
 unsigned W2Replaced()const{return w2_replaced;}
 Handle Stream()const{return stream;}''')
s=rep(s,' void* PackedMhWeightDiag(const std::string&name,U c){',''' void* W2AttentionWeight(const std::string&name,U c){
  if(!w2_frag)return PackedMhWeightDiag(name,c);
  std::string key=name+"@w2-frag-diag";auto it=weights.find(key);
  if(it==weights.end()){auto v=ReadWeights(opt.assets+"/"+name);size_t cc=size_t(c)*c;
   if(v.size()!=WeightElements(name))throw std::runtime_error("w2 weight shape");
   Fp8(v,{{0,3*cc},{3*cc,cc}});FragmentPackedMatrix(v,0,3*c,c);FragmentPackedMatrix(v,3*cc,c,c);AppendMhResidualDiagonals(v,c);
   it=weights.emplace(key,UploadWeight(v,key)).first;
  }return P(it->second);
 }
 void* PackedMhWeightDiag(const std::string&name,U c){''')
s=rep(s,'if(opt.fused_mh){Handle m{};', '''{Handle m{};api.Check(api.LoadModule(&m,(opt.modules+"/c64-wave2.hsaco").c_str()),"c64 wave2 module");modules["c64_wave2"]=m;}
if(opt.fused_mh){Handle m{};''')
s=rep(s,'if(module=="mh_window"){groups=count;threads=256;}', 'if(module=="c64_wave2"){groups=count;threads=kernel.rfind("c64_",0)==0?64:kernel.rfind("c128_",0)==0?128:256;}\n  if(module=="mh_window"){groups=count;threads=256;}')
anchor='auto packed=(identity||mapped)?input:New(size_t(n)*c);'
new='''if(c==64||c==128||c==256){++w2_calls;if(w2_mode==4||(w2_mode==1&&c==64)||(w2_mode==2&&c==128)||(w2_mode==3&&c==256)||(w2_mode==5&&c<=128)){
  if(!(identity||mapped)||!opt.grouped_mh_contract||!opt.packed_weights||!byte_feature||!opt.mh_proj_diag_fb)throw std::runtime_error("w2 requires production C64 byte-feature path");
  pdl_prev={};pdl_ffn_flags=nullptr;pdl_anyorder=false;
  auto out=New(size_t(w)*h*c/(byte_out?4:1));
  ++w2_replaced;std::string name="c"+std::to_string(c)+"_wave2"+(byte_in?"_bi":"")+(byte_out?"_bo":"");
  Run("c64_wave2",name.c_str(),n/64,P(input),w2_frag?PackedFusedMhWeightFrag(Block(block,"ffn"),c):PackedMhWeight(Block(block,"ffn"),c,false),W2AttentionWeight(Block(block,"attention"),c),P(out),w,h,ww,hh,sx,sy,U(raw?3:(block==48||block==55||block==61||block==65)?0:4));
  Stage("block"+std::to_string(block),out);return out;
 }}
 '''+anchor
s=rep(s,anchor,new);p.write_text(s)
native=(ROOT/'src/native_hip_network.h').read_text();a=native.index('hip_reference::Options o;');b=native.index('  const wchar_t*modules=',a)
options=native[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift','o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)','o.assets=argv[1]')
(OUT/'network.cpp').write_text((HERE/'runner.cpp.in').read_text().replace('/* OPTIONS */',options))
for name in ('build.ps1','run.ps1','start.ps1'):shutil.copyfile(HERE/name,OUT/name)
(OUT/'manifest.json').write_text(json.dumps({'base_source_sha256':hashlib.sha256(base.encode()).hexdigest(),'kernel_sha256':hashlib.sha256(kernel.encode()).hexdigest(),'host_source_sha256':hashlib.sha256((ROOT/'Development/HIP/hip_reference_network.h').read_bytes()).hexdigest(),'modes':{'0':'prod8 PDL baseline','1':'C64','2':'C128','3':'C256','4':'all C64/C128/C256','5':'C64+C128'},'layouts':['row','frag']},indent=2)+'\n')
print(OUT)
