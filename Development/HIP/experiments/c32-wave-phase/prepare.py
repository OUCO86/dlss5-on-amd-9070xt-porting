"""Phase ledger for the single-wave C32 kernels (hip/wave_owned_c32.inc), production recipe + per-phase instrumented twins.

Each phase twin accumulates local 20-bit SHADER_CYCLES around one code section (summed over the four query tiles where the
section sits inside a loop) and the whole kernel; one window in 32 writes {phase, whole, window, magic}. Original kernels in the
module are compiled from the unchanged source and must keep their machine code (checked by inspect.py).
Usage: prepare.py [--split]   (--split additionally defines CW_PREFIX_SPLIT 1 for both originals and twins)
"""
from pathlib import Path
import hashlib, json, shutil, sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SPLIT = '--split' in sys.argv
OUT = Path('/tmp/c32-wave-phase' + ('-split' if SPLIT else ''))
OUT.mkdir(exist_ok=True)


def rep(s, old, new):
    assert s.count(old) == 1, (old[:90], s.count(old))
    return s.replace(old, new, 1)


inc = (ROOT / 'hip/wave_owned_c32.inc').read_text()
a = inc.index('template<bool Chain,bool Finish=false')
b = inc.index('#define CW_ENTRY')
body = inc[a:b]
B = lambda n: f' if constexpr(Phase=={n})ck_t=phase_clock();\n'
E = lambda n: f' if constexpr(Phase=={n})ck_acc+=(phase_clock()-ck_t)&0xfffffu;\n'
body = rep(body, 'template<bool Chain,', 'template<uint Phase,bool Chain,')
body = rep(body, 'DEV void cw_body(', 'DEV void cw_phase_body(uint*trace,uint trace_offset,')
body = rep(body, ' uint win=bid();if(win>=windows)return;\n', ' uint win=bid();if(win>=windows)return;\n uint ck_entry=phase_clock(),ck_acc=0,ck_t=0;\n')
# loop 1: input | chain residual mix | FFN | feature pack + residual store | QKV + norm
body = rep(body, '  i2 input[2];f8 ffn[2]{};\n', '  i2 input[2];f8 ffn[2]{};\n' + B(1))
body = rep(body, '  if constexpr(Chain)for(uint part=0;part<3;part++)', E(1) + B(2) + '  if constexpr(Chain)for(uint part=0;part<3;part++)')
body = rep(body, '#if CW_ROLL_HIDDEN\n', E(2) + B(3) + '#if CW_ROLL_HIDDEN\n')
body = rep(body, '  i2 feature[2];', E(3) + B(4) + '  i2 feature[2];')
body = rep(body, '  for(uint part=0;part<3;part++){\n   uint qlane', E(4) + B(5) + '  for(uint part=0;part<3;part++){\n   uint qlane')
body = rep(body, '  __builtin_amdgcn_sched_barrier(0);\n }\n _Pragma("clang loop unroll(disable)") for(uint qt=0;qt<4;qt++){',
           E(5) + '  __builtin_amdgcn_sched_barrier(0);\n }\n _Pragma("clang loop unroll(disable)") for(uint qt=0;qt<4;qt++){')
# loop 2: scores+exp | sums+prob | AV | projection+residual+store
body = rep(body, '  h8 ex[4];\n', '  h8 ex[4];\n' + B(6))
body = rep(body, '  f8 sums{};h8 ones{};', E(6) + B(7) + '  f8 sums{};h8 ones{};')
body = rep(body, '  i2 av[2];', E(7) + B(8) + '  i2 av[2];')
body = rep(body, '  for(uint ci=0;ci<2;ci++){\n   f8 acc{};for(uint kt=0;kt<2;kt++){i2 b=matrix8(w,3072', E(8) + B(9) + '  for(uint ci=0;ci<2;ci++){\n   f8 acc{};for(uint kt=0;kt<2;kt++){i2 b=matrix8(w,3072')
body = rep(body, '  __builtin_amdgcn_sched_barrier(0);\n }\n\n if constexpr(Post){', E(9) + '  __builtin_amdgcn_sched_barrier(0);\n }\n' + B(10) + '\n if constexpr(Post){')
k = body.rstrip().rfind('}')
body = body[:k] + E(10) + ''' uint ck_exit=phase_clock();
 if constexpr(Phase==0)ck_acc=(ck_exit-ck_entry)&0xfffffu;
 if((win&31u)==trace_offset&&__builtin_amdgcn_workitem_id_x()==0){
  uint*dst=trace+(win/32u)*4u;dst[0]=ck_acc;dst[1]=(ck_exit-ck_entry)&0xfffffu;dst[2]=win;dst[3]=0xc3210000u|Phase;
 }
''' + body[k:]
helpers = '\n// Local 20-bit SHADER_CYCLES (not the serialized REALTIME message).\nDEV uint phase_clock(){uint t;__asm__ volatile("s_getreg_b32 %0, hwreg(29, 0, 20)":"=s"(t)::"memory");return t;}\n'
defines = '#define CW_ROLL_HIDDEN 1\n#define CW_ROLL_WINDOW 1\n#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n' + ('#define CW_PREFIX_SPLIT 1\n' if SPLIT else '')
code = defines + (ROOT / 'hip/c32_fused_ffn_attention.hip').read_text() + '\n' + inc + helpers + body
T = 'uint*trace,uint trace_offset'
entries = {
 'c32_wave1_chain': ('const unsigned char*in,const float*fw,const float*w,unsigned char*out,uint windows,uint mode,uint raw,uint width,uint height,uint sx,uint sy,uint prevw,uint px,uint py',
                     'true', 'in,fw,w,out,windows,mode,raw,width,height,sx,sy,prevw,px,py'),
 'c32_wave1_mapped': ('const unsigned char*in,const float*fw,const float*w,unsigned char*out,uint windows,uint mode,uint raw,uint width,uint height,uint sx,uint sy',
                      'false', 'in,fw,w,out,windows,mode,raw,width,height,sx,sy,0,0,0'),
 'c32_wave1_finish': ('const unsigned char*in,const float*fw,const float*w,float*main,float*down,uint windows,uint mode,uint raw,uint width,uint height,uint sx,uint sy,uint prevw,uint px,uint py',
                      'true,true,false', 'in,fw,w,nullptr,windows,mode,raw,width,height,sx,sy,prevw,px,py,main,down'),
 'c32_wave1_finish_dcrop': ('const unsigned char*in,const float*fw,const float*w,float*main,float*down,uint windows,uint mode,uint raw,uint width,uint height,uint sx,uint sy,uint prevw,uint px,uint py',
                            'true,true,true', 'in,fw,w,nullptr,windows,mode,raw,width,height,sx,sy,prevw,px,py,main,down'),
 'c32_wave1_post': ('const unsigned char*low,const unsigned char*skip,const float*scales,const float*fw,const float*w,const float*color,const float*headw,float*rgb,uint windows,uint width,uint height,uint sx,uint sy,float scale',
                    'false,false,false,true', 'low,fw,w,nullptr,windows,0,1,width,height,sx,sy,0,0,0,nullptr,nullptr,skip,scales,color,headw,rgb,scale'),
 'c32_wave1_prefix': ('const unsigned char*rgba,const float*history,const float*fw,const float*w,float*main,float*down,uint windows,uint mode,uint raw,uint width,uint height,uint seed,uint temporal',
                      'false,true,false,false,true', 'rgba,fw,w,nullptr,windows,mode,raw,width,height,0,0,0,0,0,main,down,nullptr,nullptr,nullptr,nullptr,nullptr,0.f,history,seed,temporal'),
}
for name, (params, targs, args) in entries.items():
    for p in range(11):
        code += f'CW_ENTRY void {name}_phase{p}({params},{T}){{cw_phase_body<{p},{targs}>(trace,trace_offset,{args});}}\n'
(OUT / 'kernel.hip').write_text(code)

(OUT / 'Development/HIP').mkdir(parents=True, exist_ok=True)
for path in (ROOT / 'Development/HIP').glob('*.h'):
    shutil.copyfile(path, OUT / 'Development/HIP' / path.name)
p = OUT / 'Development/HIP/hip_reference_network.h'
h = rep(p.read_text(), 'class Network {', 'class Network {\n' + (HERE / 'host.inc').read_text() + '\nprivate:\n')
h = rep(h, ' void Enqueue(void*rgba,void*history,void*rgb_output,U seed){', ' void Enqueue(void*rgba,void*history,void*rgb_output,U seed){phase_launch=0;')
anchor = 'void*reuse_gate_arg=adaptive_active?P(adaptive_state):nullptr;void*argv[]={static_cast<void*>(&args)...,static_cast<void*>(&reuse_gate_arg)};'
h = rep(h, anchor, '''void*reuse_gate_arg=adaptive_active?P(adaptive_state):nullptr;
 if(module=="c32_wave1"){
  unsigned index=phase_launch++;if(index>=PHASE_LAUNCHES)throw std::runtime_error("phase launch capacity");
  phase_names[index]=kernel;phase_groups[index]=groups;
  if(phase_mode){
   if(groups>PHASE_GROUPS||threads!=32)throw std::runtime_error("phase geometry");
   reuse_gate_arg=phase_buffer+(size_t(phase_frame)*PHASE_LAUNCHES+index)*PHASE_WORDS;
   kernel+="_phase"+std::to_string(phase_mode-1);
  }
 }
 void*argv[]={static_cast<void*>(&args)...,static_cast<void*>(&reuse_gate_arg),static_cast<void*>(&phase_offset)};''')
p.write_text(h)
host = (ROOT / 'src/native_hip_network.h').read_text()
a = host.index('hip_reference::Options o;'); b = host.index('  const wchar_t*modules=', a)
options = host[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift', 'o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)', 'o.assets=argv[1]')
(OUT / 'network.cpp').write_text((HERE / 'runner.cpp.in').read_text().replace('/* OPTIONS */', options))
for name in ('build.ps1', 'run.ps1', 'start.ps1'):
    shutil.copyfile(HERE / name, OUT / name)
(OUT / 'source-manifest.json').write_text(json.dumps({
 'split': SPLIT,
 'inc_sha256': hashlib.sha256(inc.encode()).hexdigest(),
 'host_sha256': hashlib.sha256((ROOT / 'Development/HIP/hip_reference_network.h').read_bytes()).hexdigest(),
 'phases': ['whole', 'input', 'chain_mix', 'ffn', 'feature_pack', 'qkv_norm', 'scores_exp', 'sums_prob', 'av', 'projection_store', 'tail'],
 'sampling': 'one window in 32, 8 capture frames rotating offsets (frame*5)%32',
}, indent=2) + '\n')
print(OUT)
