"""Build an independent two-wave C64 prototype against the current host/production modules."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];OUT=Path('/tmp/c64-wave2');OUT.mkdir(exist_ok=True)
def rep(s,a,b):
 assert s.count(a)==1,(a[:100],s.count(a))
 return s.replace(a,b,1)
base=(ROOT/'hip/multihead_fast_padded.hip').read_text()
kernel='#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_FFN_HOIST_RES 2\n#define HIP_PDL_KERNELS 0\n'+base+'\n'+(ROOT/'hip/wave_owned_mh.inc').read_text()
# Derive attention-only core from the exact fused prototype, sharing its math.
core=(ROOT/'hip/wave_owned_mh.inc').read_text()
attention=core[core.index(' // One wave owns all keys'):core.index('#define W2_KERNEL')]
attention=rep(attention,'i2 a=w2_load<C>(plane0,qt,ct);','''i2 a;
#if W2_DIRECT_FEATURE
   __builtin_memcpy(&a,feature+w2_pixel(win,qt*16+rc,workw)*C+ct*16+gr*8,8);
#else
   a=w2_load<C>(plane0,qt,ct);
#endif
''')
setup=(ROOT/'hip/wave_owned_attention_setup.inc').read_text()
kernel+='\n#if !W2_DEFER_Q\n'+setup+attention+'\n'+(ROOT/'hip/wave_owned_attention_exports.inc').read_text()+'\n#endif\n'
(OUT/'kernel.hip').write_text(kernel)
(OUT/'kernel-frag.hip').write_text('#define W2_FRAGMENT_WEIGHTS 1\n'+kernel)
(OUT/'kernel-defer.hip').write_text('#define W2_DEFER_Q 1\n'+kernel)
(OUT/'kernel-frag-defer.hip').write_text('#define W2_FRAGMENT_WEIGHTS 1\n#define W2_DEFER_Q 1\n'+kernel)
(OUT/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (ROOT/'Development/HIP').glob('*.h'):shutil.copyfile(p,OUT/'Development/HIP'/p.name)
p=OUT/'Development/HIP/hip_reference_network.h';s=p.read_text()
s=rep(s,'class Network {','class Network {\n unsigned w2_mode=0,w2_calls=0,w2_replaced=0;bool w2_frag=std::getenv("W2_FRAG")&&std::string(std::getenv("W2_FRAG"))=="1";')
s=rep(s,' Handle Stream()const{return stream;}',''' void W2Mode(unsigned mode){if(mode>7)throw std::runtime_error("w2 mode");Synchronize();w2_mode=mode;w2_calls=0;w2_replaced=0;}
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
new='''if(c==64||c==128||c==256){++w2_calls;if(w2_mode==4||(w2_mode==1&&c==64)||(w2_mode==2&&c==128)||(w2_mode==3&&c==256)||((w2_mode==5||w2_mode==7)&&c<=128)){
  if(!(identity||mapped)||!opt.grouped_mh_contract||!opt.packed_weights||!byte_feature||!opt.mh_proj_diag_fb)throw std::runtime_error("w2 requires production C64 byte-feature path");
  pdl_prev={};pdl_ffn_flags=nullptr;pdl_anyorder=false;
  auto out=New(size_t(w)*h*c/(byte_out?4:1));
  ++w2_replaced;std::string name="c"+std::to_string(c)+"_wave2"+(byte_in?"_bi":"")+(byte_out?"_bo":"");
  Run("c64_wave2",name.c_str(),n/64,P(input),w2_frag?PackedFusedMhWeightFrag(Block(block,"ffn"),c):PackedMhWeight(Block(block,"ffn"),c,false),W2AttentionWeight(Block(block,"attention"),c),P(out),w,h,ww,hh,sx,sy,U(raw?3:(block==48||block==55||block==61||block==65)?0:4));
  Stage("block"+std::to_string(block),out);return out;
 }}
 '''+anchor
s=rep(s,anchor,new)
anchor='  if((c==64||c==128||c==256)&&opt.packed_weights&&opt.fused_mh&&opt.fp8_av&&opt.fp8_normalized)'
s=rep(s,anchor,'''  if((w2_mode==6||w2_mode==7)&&c==256){
   if(!feature_byte||!ready_norm||!opt.mh_proj_diag_fb)throw std::runtime_error("attention-only production inputs required");
   auto out=New((cropw?size_t(cropw)*croph:size_t(n))*c/(out_byte?4:1));
   unsigned*af=nullptr;unsigned ae=0;const unsigned*ff=pdl_ffn_flags;unsigned fe=pdl_ffn_epoch;
   if(ff){af=PdlSlot(1,c,w,h,8u);ae=pdl_last_target;pdl_anyorder=true;}
   ++w2_replaced;
   Run("c64_wave2",out_byte?"c256_attn_wave_bo":"c256_attn_wave",windows,P(norm),W2AttentionWeight(aw,c),P(input),P(out),cropw?cropw:w,cropw?croph:h,w,h,sx,sy,U(raw?3:rounded_output?0:4),ff,fe,af);
   pdl_anyorder=false;pdl_prev=ff?PdlPrev{af,ae,w,sx,sy}:PdlPrev{};pdl_ffn_flags=nullptr;return out;
  }
'''+anchor)
p.write_text(s)
native=(ROOT/'src/native_hip_network.h').read_text();a=native.index('hip_reference::Options o;');b=native.index('  const wchar_t*modules=',a)
options=native[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift','o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)','o.assets=argv[1]')+'\n o.wave_owned=false; // experimental mode selection owns dispatch\n'
(OUT/'network.cpp').write_text((HERE/'runner.cpp.in').read_text().replace('/* OPTIONS */',options))
for name in ('build.ps1','run.ps1','start.ps1'):shutil.copyfile(HERE/name,OUT/name)
(OUT/'manifest.json').write_text(json.dumps({'base_source_sha256':hashlib.sha256(base.encode()).hexdigest(),'kernel_sha256':hashlib.sha256(kernel.encode()).hexdigest(),'host_source_sha256':hashlib.sha256((ROOT/'Development/HIP/hip_reference_network.h').read_bytes()).hexdigest(),'modes':{'0':'prod8 PDL baseline','1':'C64','2':'C128','3':'C256','4':'all C64/C128/C256','5':'C64+C128','6':'C256 attention-only','7':'C64/C128 fused + C256 attention-only'},'layouts':['row','frag']},indent=2)+'\n')
print(OUT)
