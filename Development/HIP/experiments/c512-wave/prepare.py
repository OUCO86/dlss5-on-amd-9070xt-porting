"""C512 one-head-one-wave attention/projection prototype on top of the current production (prod8 + wave-owned 46 + PDL).
Writes /tmp/c512-wave: kernel.hip (module c512-wave.hsaco), network.cpp (production host copy with W2Mode 0/1)."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];OUT=Path('/tmp/c512-wave');OUT.mkdir(exist_ok=True)
def rep(s,a,b):
 assert s.count(a)==1,(a[:100],s.count(a))
 return s.replace(a,b,1)
core=(ROOT/'hip/wave_owned_mh.inc').read_text()
helpers=core[:core.index('template<uint C,bool ByteIn,bool ByteOut>\nDEV void swin_wave2_body')]
attention=core[core.index(' // One wave owns all keys'):core.index(" w2_sync();\n // All heads' AV ready")]
qloop=' for(uint qt=0;qt<4;qt++){\n#if W2_ROLL_QUERY && !W2_DEFER_Q'
assert attention.count(qloop)==1
attention=attention.replace(qloop,' for(uint qt=q0;qt<q0+QN;qt++){\n#if W2_ROLL_QUERY && !W2_DEFER_Q')
assert 'W2_DEFER_Q' in attention and 'w2_store<C>(plane1,qt,head*2+ci,a)' in attention
body=rep((HERE/'c512_attention.inc').read_text(),'/*ATTENTION_CORE*/\n',attention)
prefix='#define W2_FRAGMENT_WEIGHTS 1\n#define W2_DEFER_Q 0\n#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_FFN_HOIST_RES 2\n#define HIP_PDL_KERNELS 0\n'
kernel=prefix+(ROOT/'hip/multihead_fast_padded.hip').read_text()+'\n'+helpers+'\n'+body
(OUT/'kernel.hip').write_text(kernel)
(OUT/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (ROOT/'Development/HIP').glob('*.h'):shutil.copyfile(p,OUT/'Development/HIP'/p.name)
p=OUT/'Development/HIP/hip_reference_network.h';s=p.read_text()
s=rep(s,'class Network {','class Network {\n unsigned w2_mode=0,w2_calls=0,w2_replaced=0;')
s=rep(s,' Handle Stream()const{return stream;}',''' void W2Mode(unsigned mode){if(mode>4)throw std::runtime_error("c512 mode");Synchronize();w2_mode=mode;w2_calls=0;w2_replaced=0;}
 unsigned W2Calls()const{return w2_calls;}
 unsigned W2Replaced()const{return w2_replaced;}
 Handle Stream()const{return stream;}''')
s=rep(s,'if(opt.fused_mh){Handle m{};','''{Handle m{};api.Check(api.LoadModule(&m,(opt.modules+"/c512-wave.hsaco").c_str()),"c512 wave module");modules["c512_wave"]=m;}
if(opt.fused_mh){Handle m{};''')
s=rep(s,'  if(module=="mh_window"){groups=count;threads=256;}','  if(module=="c512_wave"){groups=count;threads=kernel=="c512_attn_wave2"?1024:512;}\n  if(module=="mh_window"){groups=count;threads=256;}')
anchor='  if((c==64||c==128||c==256)&&opt.packed_weights&&opt.fused_mh&&opt.fp8_av&&opt.fp8_normalized)'
s=rep(s,anchor,'''  const bool c5=c==512&&ready_norm&&opt.fp8_normalized&&opt.fused_mh&&opt.fp8_av&&opt.c512_proj_frag;
  if(c5){++w2_calls;if(w2_mode==1||w2_mode==2){
   if(feature_byte||out_byte)throw std::runtime_error("c512 wave feature/output format");
   auto out=New((cropw?size_t(cropw)*croph:size_t(n))*c);++w2_replaced;
   Run("c512_wave",w2_mode==2?"c512_attn_wave2":"c512_attn_wave",windows,P(norm),PackedMhWeightQkvFrag(aw,512),P(input),P(out),w,h,cropw,croph,sx,sy,U(raw?3:0));
   return out;}}
'''+anchor)
a='Run("mh_fused",opt.fp8_av?"mh_attention_fused_fp8_out":opt.fp8_normalized?"mh_attention_fused_fp8":"mh_attention_fused",size_t(windows)*heads,P(norm),weights,P(av),w,h,c);'
s=rep(s,a,a+'if(c5&&w2_mode==3){++w2_replaced;'+a+'}')
a='if(cropw)if(opt.c512_proj_frag&&c==512)Run("mh_fast","mh_attention_project_frag_c512",size_t(n)*c,P(av),P(input),PackedMhWeightQkvFrag(aw,512),P(out),n,U(raw?3:0),cropw,croph,w,sx,sy);'
s=rep(s,a,'if(c5&&w2_mode==4&&cropw){++w2_replaced;Run("mh_fast","mh_attention_project_frag_c512",size_t(n)*c,P(av),P(input),PackedMhWeightQkvFrag(aw,512),P(out),n,U(raw?3:0),cropw,croph,w,sx,sy);}'+a)
p.write_text(s)
native=(ROOT/'src/native_hip_network.h').read_text();a=native.index('hip_reference::Options o;');b=native.index('  const wchar_t*modules=',a)
options=native[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift','o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)','o.assets=argv[1]')
assert 'o.width=W' in options and 'o.assets=argv[1]' in options
(OUT/'network.cpp').write_text((HERE/'runner.cpp.in').read_text().replace('/* OPTIONS */',options))
for name in ('build.ps1','run.ps1'):shutil.copyfile(HERE/name,OUT/name)
(OUT/'manifest.json').write_text(json.dumps({'kernel_sha256':hashlib.sha256(kernel.encode()).hexdigest(),'host_source_sha256':hashlib.sha256((ROOT/'Development/HIP/hip_reference_network.h').read_bytes()).hexdigest(),'modes':{'0':'production: prod8 + wave-owned 46 + PDL=1','1':'+ C512 attention/projection one head per wave','2':'+ C512, two waves per head (query tiles split)'}},indent=2)+'\n')
print(OUT)
