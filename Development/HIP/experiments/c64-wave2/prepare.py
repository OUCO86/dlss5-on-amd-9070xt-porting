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
(OUT/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (ROOT/'Development/HIP').glob('*.h'):shutil.copyfile(p,OUT/'Development/HIP'/p.name)
p=OUT/'Development/HIP/hip_reference_network.h';s=p.read_text()
s=rep(s,'class Network {','class Network {\n unsigned w2_mode=0,w2_calls=0;')
s=rep(s,' Handle Stream()const{return stream;}',''' void W2Mode(unsigned mode){if(mode>1)throw std::runtime_error("w2 mode");Synchronize();w2_mode=mode;w2_calls=0;}
 unsigned W2Calls()const{return w2_calls;}
 Handle Stream()const{return stream;}''')
s=rep(s,'if(opt.fused_mh){Handle m{};', '''{Handle m{};api.Check(api.LoadModule(&m,(opt.modules+"/c64-wave2.hsaco").c_str()),"c64 wave2 module");modules["c64_wave2"]=m;}
if(opt.fused_mh){Handle m{};''')
s=rep(s,'if(module=="mh_window"){groups=count;threads=256;}', 'if(module=="c64_wave2"){groups=count;threads=64;}\n  if(module=="mh_window"){groups=count;threads=256;}')
anchor='auto packed=(identity||mapped)?input:New(size_t(n)*c);'
new='''if(c==64){++w2_calls;if(w2_mode){
  if(!(identity||mapped)||!opt.grouped_mh_contract||!opt.packed_weights||!byte_feature||!opt.mh_proj_diag_fb)throw std::runtime_error("w2 requires production C64 byte-feature path");
  pdl_prev={};pdl_ffn_flags=nullptr;pdl_anyorder=false;
  auto out=New(size_t(w)*h*c/(byte_out?4:1));
  std::string name=std::string("c64_wave2")+(byte_in?"_bi":"")+(byte_out?"_bo":"");
  Run("c64_wave2",name.c_str(),n/64,P(input),PackedMhWeight(Block(block,"ffn"),64,false),PackedMhWeightDiag(Block(block,"attention"),64),P(out),w,h,ww,hh,sx,sy,U(raw?3:block==65?0:4));
  Stage("block"+std::to_string(block),out);return out;
 }}
 '''+anchor
s=rep(s,anchor,new);p.write_text(s)
native=(ROOT/'src/native_hip_network.h').read_text();a=native.index('hip_reference::Options o;');b=native.index('  const wchar_t*modules=',a)
options=native[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift','o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)','o.assets=argv[1]')
(OUT/'network.cpp').write_text((HERE/'runner.cpp.in').read_text().replace('/* OPTIONS */',options))
for name in ('build.ps1','run.ps1','start.ps1'):shutil.copyfile(HERE/name,OUT/name)
(OUT/'manifest.json').write_text(json.dumps({'base_source_sha256':hashlib.sha256(base.encode()).hexdigest(),'kernel_sha256':hashlib.sha256(kernel.encode()).hexdigest(),'host_source_sha256':hashlib.sha256((ROOT/'Development/HIP/hip_reference_network.h').read_bytes()).hexdigest(),'modes':{'0':'prod8 PDL baseline','1':'C64 fused two-wave, sequential32 normalization'}},indent=2)+'\n')
print(OUT)
