"""Sparse per-wave stage/whole timing with pointer arguments, no per-launch sync."""
from pathlib import Path
import hashlib
import json
import re
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = Path('/tmp/c32-phase-current')
OUT.mkdir(exist_ok=True)


def rep(s, old, new):
    assert s.count(old) == 1, (old[:80], s.count(old))
    return s.replace(old, new, 1)


s = (ROOT / 'hip/c32_fused_ffn_attention.hip').read_text()
a = s.index('template<bool HalfOutput,bool Mapped=false')
b = s.index('\nKERNEL ', a)
body = s[a:b]
body = rep(body, 'template<bool HalfOutput,', 'template<uint Phase,bool HalfOutput,')
body = rep(body, 'DEV void c32_fused_body(', 'DEV void c32_phase_body(uint*trace,uint trace_offset,')
body = rep(body, ' __attribute__((shared)) Scratch scratch;', ''' __attribute__((shared)) Scratch scratch;
 uint clock_entry=phase_clock(),clock_start=0,clock_stop=0;
 if constexpr(Phase==1)clock_start=clock_entry;''')
anchor = '#if HIP_C32_LOCAL_FFN_SYNC\n sync_owned_rows();\n#else\n sync_window();\n#endif\n'
assert body.count(anchor) == 2
body = body.replace(anchor, ''' if constexpr(Phase==1)clock_stop=phase_clock();
 if constexpr(Phase==2)clock_start=phase_clock();
 if constexpr(Phase==7)clock_start=phase_clock();
''' + anchor, 1)
body = rep(body, '\n#if HIP_C32_FOLDED_FFN\n', '''
 if constexpr(Phase==7)clock_stop=phase_clock();
 if constexpr(Phase==8)clock_start=phase_clock();
#if HIP_C32_FOLDED_FFN
''')
body = rep(body, '#if HIP_C32_ABLATE!=1\n C32_LOOP for(uint t=0;t<8;t++)', ''' if constexpr(Phase==8)clock_stop=phase_clock();
 if constexpr(Phase==9)clock_start=phase_clock();
#if HIP_C32_ABLATE!=1
 C32_LOOP for(uint t=0;t<8;t++)''')
body = rep(body, '#if HIP_C32_ALIAS_FFN_V && HIP_C32_REGISTER_FFN\n', ''' if constexpr(Phase==9)clock_stop=phase_clock();
 if constexpr(Phase==10)clock_start=phase_clock();
#if HIP_C32_ALIAS_FFN_V && HIP_C32_REGISTER_FFN
''')
body = rep(body, ' // A single raw QKV plane is reused after its norm has been packed separately.', ''' if constexpr(Phase==2)clock_stop=phase_clock();
 if constexpr(Phase==3)clock_start=phase_clock();
 if constexpr(Phase==10)clock_stop=phase_clock();
 // A single raw QKV plane is reused after its norm has been packed separately.''')
body = rep(body, ' // Q/K packed rows: 36-byte stride. Exponent values stored exactly as half bits.', ''' if constexpr(Phase==3)clock_stop=phase_clock();
 if constexpr(Phase==4)clock_start=phase_clock();
 // Q/K packed rows: 36-byte stride. Exponent values stored exactly as half bits.''')
body = rep(body, ' ATTN_SYNC();\n#if HIP_C32_TRANSPOSED_TAIL', ''' ATTN_SYNC();
 if constexpr(Phase==4)clock_stop=phase_clock();
 if constexpr(Phase==5)clock_start=phase_clock();
#if HIP_C32_TRANSPOSED_TAIL''')
body = rep(body, '\n if constexpr(Finish){\n', '''
 if constexpr(Phase==5)clock_stop=phase_clock();
 if constexpr(Phase==6)clock_start=phase_clock();
 if constexpr(Finish){
''')
k = body.rstrip().rfind('}')
body = body[:k] + ''' uint clock_exit=phase_clock();
 if constexpr(Phase==6)clock_stop=clock_exit;
 if constexpr(Phase==0){clock_start=clock_entry;clock_stop=clock_exit;}
 if((window&31u)==trace_offset && (tid&31u)==0){
  uint*dst=trace+((window/32u)*4u+wave)*4u;
  dst[0]=(clock_stop-clock_start)&0xfffffu;
  dst[1]=(clock_exit-clock_entry)&0xfffffu;
  dst[2]=window;dst[3]=0xc3200000u|Phase;
 }
''' + body[k:]
helpers = '''
// Local 20-bit SHADER_CYCLES, not the globally serialized REALTIME message.
DEV uint phase_clock(){uint t;__asm__ volatile("s_getreg_b32 %0, hwreg(29, 0, 20)":"=s"(t)::"memory");return t;}
'''
code = '#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_C32_DIAG_WEIGHTS 1\n'+s+helpers+body
names = [
 'c32_fast_ffn_attention_fused_half_prefix_finish_main8',
 'c32_fast_ffn_attention_fused_half_mapped',
 'c32_fast_ffn_attention_fused_half_chain',
 'c32_fast_ffn_attention_fused_half_chain_finish_dcrop',
 'c32_fast_ffn_attention_fused_half_chain_finish',
 'c32_post_merge_head_half',
]
for name in names:
    entry = next(x for x in s[b:].splitlines() if x.startswith('void '+name+'('))
    for phase in range(11):
        line = entry.replace('void '+name+'(', f'void {name}_phase{phase}(', 1)
        line = rep(line, '){c32_fused_body<', f',uint*trace,uint trace_offset){{c32_phase_body<{phase},')
        line = rep(line, '>(', '>(trace,trace_offset,')
        code += '\nKERNEL __attribute__((amdgpu_flat_work_group_size(128,128))) C32_OCC\n'+line+'\n'
(OUT / 'kernel.hip').write_text(code)

(OUT / 'Development/HIP').mkdir(parents=True, exist_ok=True)
for path in (ROOT / 'Development/HIP').glob('*.h'):
    shutil.copyfile(path, OUT / 'Development/HIP' / path.name)
p = OUT / 'Development/HIP/hip_reference_network.h'
h = rep(p.read_text(), 'class Network {', 'class Network {\n'+(HERE/'host.inc').read_text()+'\nprivate:\n')
h = rep(h, ' void Enqueue(void*rgba,void*history,void*rgb_output,U seed){',
        ' void Enqueue(void*rgba,void*history,void*rgb_output,U seed){phase_launch=0;')
anchor = 'void*reuse_gate_arg=adaptive_active?P(adaptive_state):nullptr;void*argv[]={static_cast<void*>(&args)...,static_cast<void*>(&reuse_gate_arg)};'
replacement = '''void*reuse_gate_arg=adaptive_active?P(adaptive_state):nullptr;
 if(module=="c32_fused_ffn"){
  unsigned index=phase_launch++;if(index>=PHASE_LAUNCHES)throw std::runtime_error("phase launch capacity");
  if(phase_mode){
   unsigned gg=groups?groups:unsigned((count+255ull)/256);if(gg>PHASE_GROUPS||threads!=128)throw std::runtime_error("phase geometry");
   phase_names[index]=kernel;phase_groups[index]=gg;
   reuse_gate_arg=phase_buffer+(size_t(phase_frame)*PHASE_LAUNCHES+index)*PHASE_WORDS;
   kernel+="_phase"+std::to_string(phase_mode-1);
  }
 }
 void*argv[]={static_cast<void*>(&args)...,static_cast<void*>(&reuse_gate_arg),static_cast<void*>(&phase_offset)};'''
h = rep(h, anchor, replacement)
p.write_text(h)
host = (ROOT / 'src/native_hip_network.h').read_text()
a = host.index('hip_reference::Options o;'); b = host.index('  const wchar_t*modules=', a)
options = host[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift', 'o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)', 'o.assets=argv[1]')
(OUT/'network.cpp').write_text((HERE/'runner.cpp.in').read_text().replace('/* OPTIONS */',options))
for name in ('build.ps1','run.ps1','start.ps1'):
    shutil.copyfile(HERE/name, OUT/name)
(OUT/'source-manifest.json').write_text(json.dumps({
 'source_sha256':hashlib.sha256(s.encode()).hexdigest(),
 'host_sha256':hashlib.sha256((ROOT/'Development/HIP/hip_reference_network.h').read_bytes()).hexdigest(),
 'instrumented_host_sha256':hashlib.sha256((HERE/'host.inc').read_bytes()).hexdigest(),
 'phases':['whole','staging','ffn+publish','qkv+norm','attention+publish','projection','tail','initial_sync','residual_init','ffn_math','ffn_publish'],
 'sampling':'one of 32 groups, all four waves; 8 capture frames rotate offsets (frame*5)%32',
},indent=2)+'\n')
print(OUT)
