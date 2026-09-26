"""C512 FFN chain (mix -> split FFN fused -> split projection -> QKV normalize) on the current production
(prod8 + wave-owned 46 + PDL=1). Writes /tmp/c512-ffn: network.cpp (production host copy with C5Mode) and kernel.hip
(candidate module c512-ffn.hsaco, only when candidates exist).
Modes: 0 production; 1..4 duplicate one chain kernel (mix / ffn_fused_t8 / projection_frag / qkv_norm) for marginal cost;
5.. candidates (see README)."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];OUT=Path('/tmp/c512-ffn');OUT.mkdir(exist_ok=True)
def rep(s,a,b):
 assert s.count(a)==1,(a[:100],s.count(a))
 return s.replace(a,b,1)
(OUT/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (ROOT/'Development/HIP').glob('*.h'):shutil.copyfile(p,OUT/'Development/HIP'/p.name)
p=OUT/'Development/HIP/hip_reference_network.h';s=p.read_text()
s=rep(s,'class Network {','class Network {\n unsigned c5_mode=0,c5_calls=0,c5_replaced=0;')
s=rep(s,' Handle Stream()const{return stream;}',''' void C5Mode(unsigned mode){Synchronize();c5_mode=mode;c5_calls=0;c5_replaced=0;}
 unsigned C5Calls()const{return c5_calls;}
 unsigned C5Replaced()const{return c5_replaced;}
 Handle Stream()const{return stream;}''')
chain=[
 'Run("deep","split_mix_blocked_h16w",size_t(n)*512,P(packed),PackedSplitFfnWeightMixHalf(Block(block,"ffwd")),P(mixed),n);',
 'Run("deep","split_ffn_fused_fp8_t8",size_t(n)*512,P(mixed),opt.split_mix_h16w?PackedSplitFfnWeightMixHalf(Block(block,"ffwd")):PackedSplitFfnWeight(Block(block,"ffwd")),P(contract),P(contract8),n);',
 'if(opt.c512_proj_tiles)Run("deep","split_projection_frag",size_t(n)*512,P(contract8),PackedSplitProjectionFrag(Block(block,"ffwd-projection")),P(packed),P(ffn),P(ffn8),n);',
 'Run("mh_fast","mh_qkv_normalize_frag_c512",size_t(n)*1536,P(ffn8),PackedMhWeightQkvFrag(Block(block,"attention"),512),P(producer_norm),n);']
for k,st in enumerate(chain,1):
 pre='++c5_calls;' if k==1 else ''
 cond=''
 if st.startswith('if(opt.c512_proj_tiles)'):cond='if(opt.c512_proj_tiles)';st2=st[len(cond):]
 else:st2=st
 s=rep(s,st,cond+'{'+pre+'if(c5_mode=='+str(k)+'){++c5_replaced;'+st2+'}'+st2+'}')
s=rep(s,'  if(module=="mh_window"){groups=count;threads=256;}','  if(module=="c512_ffn"||module=="c512_deep"){groups=count/1024;threads=32;}\n  if(module=="mh_window"){groups=count;threads=256;}')
mx=chain[0];s=rep(s,'if(c5_mode==1){++c5_replaced;'+mx+'}'+mx,'if(c5_mode==1){++c5_replaced;'+mx+'}if(c5_mode==10||c5_mode==11||c5_mode==12){++c5_replaced;'+mx.replace('Run("deep","split_mix_blocked_h16w",size_t(n)*512','Run("c512_deep","split_mix_blocked_h16w_m32",size_t((n+31)/32*32)*256')+'}else '+mx)
pj=chain[2][len('if(opt.c512_proj_tiles)'):];s=rep(s,'if(c5_mode==3){++c5_replaced;'+pj+'}'+pj,'if(c5_mode==3){++c5_replaced;'+pj+'}if(c5_mode==9||c5_mode==11){if(c5_mode==9)++c5_replaced;'+pj.replace('Run("deep","split_projection_frag",size_t(n)*512','Run("c512_deep","split_projection_frag_m32",size_t((n+31)/32*32)*256')+'}else '+pj)
s=rep(s,'if(opt.fused_mh){Handle m{};','''{Handle m{};api.Check(api.LoadModule(&m,(opt.modules+"/c512-ffn.hsaco").c_str()),"c512 ffn module");modules["c512_ffn"]=m;}{Handle m{};api.Check(api.LoadModule(&m,(opt.modules+"/c512-deep.hsaco").c_str()),"c512 deep module");modules["c512_deep"]=m;}
if(opt.fused_mh){Handle m{};''')
q=chain[3];s=rep(s,'if(c5_mode==4){++c5_replaced;'+q+'}'+q,'if(c5_mode==4){++c5_replaced;'+q+'}if(c5_mode==11||c5_mode==12){'+q.replace('Run("mh_fast","mh_qkv_normalize_frag_c512",size_t(n)*1536','Run("c512_ffn","mh_qkv_normalize_frag_c512_m32",size_t((n+31)/32*32)*768')+'}else if(c5_mode==5){++c5_replaced;'+q.replace('Run("mh_fast","mh_qkv_normalize_frag_c512"','Run("c512_ffn","mh_qkv_normalize_frag_c512_wide"')+'}else if(c5_mode==6){++c5_replaced;'+q.replace('Run("mh_fast","mh_qkv_normalize_frag_c512",size_t(n)*1536','Run("c512_ffn","mh_qkv_normalize_frag_c512_m32",size_t((n+31)/32*32)*768')+'}else if(c5_mode==7){++c5_replaced;'+q.replace('Run("mh_fast","mh_qkv_normalize_frag_c512",size_t(n)*1536','Run("c512_ffn","mh_qkv_normalize_frag_c512_m48",size_t((n+47)/48*48)*512')+'}else if(c5_mode==8){++c5_replaced;'+q.replace('Run("mh_fast","mh_qkv_normalize_frag_c512",size_t(n)*1536','Run("c512_ffn","mh_qkv_normalize_frag_c512_m64",size_t((n+63)/64*64)*384')+'}else '+q)
p.write_text(s)
prefix='#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_FFN_HOIST_RES 2\n#define HIP_PDL_KERNELS 0\n'
kernel=prefix+(ROOT/'hip/multihead_fast_padded.hip').read_text()+'\n'+(HERE/'qkv_wide.inc').read_text()
(OUT/'kernel.hip').write_text(kernel)
dprefix='#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_BRANCHLESS_F 1\n'
(OUT/'deep.hip').write_text(dprefix+(ROOT/'hip/deep_fast.hip').read_text()+'\n'+(HERE/'deep_m32.inc').read_text())
native=(ROOT/'src/native_hip_network.h').read_text();a=native.index('hip_reference::Options o;');b=native.index('  const wchar_t*modules=',a)
options=native[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift','o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)','o.assets=argv[1]')
assert 'o.width=W' in options and 'o.assets=argv[1]' in options
(OUT/'network.cpp').write_text((HERE/'runner.cpp.in').read_text().replace('/* OPTIONS */',options))
for name in ('build.ps1','run.ps1'):
 if (HERE/name).exists():shutil.copyfile(HERE/name,OUT/name)
(OUT/'manifest.json').write_text(json.dumps({'host_source_sha256':hashlib.sha256((ROOT/'Development/HIP/hip_reference_network.h').read_bytes()).hexdigest(),'modes':{'0':'production','1':'dup mix','2':'dup ffn_fused_t8','3':'dup projection_frag','4':'dup qkv_norm','5':'qkv_norm with LDS-staged 128-bit byte stores','6':'mode 5 + 32 tokens per wave','7':'48 tokens per wave','8':'64 tokens per wave','9':'split_projection_frag 32 tokens/wave','10':'split_mix_h16w 32 tokens/wave','11':'qkv m32 + projection m32 + mix m32','12':'qkv m32 + mix m32'}},indent=2)+'\n')
print(OUT)
