from pathlib import Path
import runpy,shutil,json,hashlib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];OUT=Path('/tmp/wave-owned-combined');OUT.mkdir(exist_ok=True)
runpy.run_path(str(HERE.parent/'c64-wave2/prepare.py'))
def rep(s,a,b):
 assert s.count(a)==1,(a[:100],s.count(a))
 return s.replace(a,b,1)
(OUT/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in Path('/tmp/c64-wave2/Development/HIP').glob('*.h'):shutil.copyfile(p,OUT/'Development/HIP'/p.name)
p=OUT/'Development/HIP/hip_reference_network.h';s=p.read_text()
s=rep(s,'class Network {','class Network {\n unsigned cw_mode=0,cw_calls=0,cw_replaced=0;')
s=rep(s,'if(mode>7)throw std::runtime_error("w2 mode");Synchronize();w2_mode=mode;w2_calls=0;w2_replaced=0;','if(mode>3)throw std::runtime_error("combined mode");Synchronize();w2_mode=(mode==1||mode==3)?7:0;cw_mode=(mode==2||mode==3);w2_calls=w2_replaced=cw_calls=cw_replaced=0;')
s=rep(s,'unsigned W2Calls()const{return w2_calls;}','unsigned W2Calls()const{return w2_calls+cw_calls;}')
s=rep(s,'unsigned W2Replaced()const{return w2_replaced;}','unsigned W2Replaced()const{return w2_replaced+cw_replaced;}')
s=rep(s,'if(opt.fused_mh){Handle m{};','''{Handle m{};api.Check(api.LoadModule(&m,(opt.modules+"/c32-wave1.hsaco").c_str()),"C32 module");modules["c32_wave1"]=m;}
if(opt.fused_mh){Handle m{};''')
s=rep(s,'  U count=Count(n),threads=256;unsigned groups=0;std::string module=m,kernel=name;','''  U count=Count(n),threads=256;unsigned groups=0;std::string module=m,kernel=name;
  static const std::map<std::string,std::string> cw_kernels={
   {"c32_fast_ffn_attention_fused_half_chain","c32_wave1_chain"},
   {"c32_fast_ffn_attention_fused_half_mapped","c32_wave1_mapped"},
   {"c32_fast_ffn_attention_fused_half_chain_finish","c32_wave1_finish"},
   {"c32_fast_ffn_attention_fused_half_chain_finish_dcrop","c32_wave1_finish_dcrop"},
   {"c32_post_merge_head_half","c32_wave1_post"},
   {"c32_fast_ffn_attention_fused_half_prefix_finish_main8","c32_wave1_prefix"}};
  auto cw=cw_kernels.find(kernel);if(cw!=cw_kernels.end()){++cw_calls;if(cw_mode){++cw_replaced;module="c32_wave1";kernel=cw->second;threads=32;groups=count;}}
''')
p.write_text(s)
native=(ROOT/'src/native_hip_network.h').read_text();a=native.index('hip_reference::Options o;');b=native.index('  const wchar_t*modules=',a)
options=native[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift','o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)','o.assets=argv[1]')+'\n o.wave_owned=false; // experimental mode selection owns dispatch\n'
runner=(HERE.parent/'c32-wave1/runner.cpp.in').read_text().replace('candidates{1,2,3,4}','candidates{1,2,3}').replace('m>8','m>3').replace('candidate 1..8','candidate 1..3').replace('{0,4,2,2,8,1,9,1,10}','{0,36,10,46}').replace('calls!=frames*10','calls!=frames*46').replace('net.W2Calls()!=10','net.W2Calls()!=46').replace('PASS C32 one-wave','PASS combined wave ownership')
(OUT/'network.cpp').write_text(runner.replace('/* OPTIONS */',options))
for name in ['prepare-modules.ps1','run.ps1']:shutil.copyfile(HERE/name,OUT/name)
(OUT/'manifest.json').write_text(json.dumps({'generated_host_sha256':hashlib.sha256(s.encode()).hexdigest(),'modes':{'0':'prod8','1':'MH best C64/128 fused + C256 attention','2':'C32 all ten','3':'both'}},indent=2)+'\n')
print(OUT)
