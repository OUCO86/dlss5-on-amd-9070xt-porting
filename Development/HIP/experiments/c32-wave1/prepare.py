from pathlib import Path
import shutil,json,hashlib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];OUT=Path('/tmp/c32-wave1');OUT.mkdir(exist_ok=True)
def rep(s,a,b):
 assert s.count(a)==1,(a[:80],s.count(a))
 return s.replace(a,b,1)
base=(ROOT/'hip/c32_fused_ffn_attention.hip').read_text()
kernel='#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n'+base+'\n'+(HERE/'kernel.inc').read_text();(OUT/'kernel.hip').write_text(kernel)
(OUT/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (ROOT/'Development/HIP').glob('*.h'):shutil.copyfile(p,OUT/'Development/HIP'/p.name)
p=OUT/'Development/HIP/hip_reference_network.h';s=p.read_text()
s=rep(s,'class Network {','class Network {\n unsigned w2_mode=0,w2_calls=0,w2_replaced=0;')
s=rep(s,' Handle Stream()const{return stream;}',''' void W2Mode(unsigned mode){if(mode>1)throw std::runtime_error("c32 mode");Synchronize();w2_mode=mode;w2_calls=w2_replaced=0;}
 unsigned W2Calls()const{return w2_calls;}unsigned W2Replaced()const{return w2_replaced;}
 Handle Stream()const{return stream;}''')
s=rep(s,'if(opt.fused_mh){Handle m{};','''{Handle m{};api.Check(api.LoadModule(&m,(opt.modules+"/c32-wave1.hsaco").c_str()),"c32-wave1 module");modules["c32_wave1"]=m;}
if(opt.fused_mh){Handle m{};''')
s=rep(s,'  U count=Count(n),threads=256;unsigned groups=0;std::string module=m,kernel=name;','''  U count=Count(n),threads=256;unsigned groups=0;std::string module=m,kernel=name;
  if(kernel=="c32_fast_ffn_attention_fused_half_chain"){++w2_calls;if(w2_mode){++w2_replaced;module="c32_wave1";kernel="c32_wave1_chain";groups=count;threads=32;}}''')
p.write_text(s)
native=(ROOT/'src/native_hip_network.h').read_text();a=native.index('hip_reference::Options o;');b=native.index('  const wchar_t*modules=',a)
options=native[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift','o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)','o.assets=argv[1]')
runner=(HERE/'runner.cpp.in').read_text();(OUT/'network.cpp').write_text(runner.replace('/* OPTIONS */',options))
for name in ['build.ps1','run.ps1']:shutil.copyfile(HERE/name,OUT/name)
(OUT/'manifest.json').write_text(json.dumps({'kernel_sha256':hashlib.sha256(kernel.encode()).hexdigest(),'host_sha256':hashlib.sha256(s.encode()).hexdigest()},indent=2)+'\n')
print(OUT)
