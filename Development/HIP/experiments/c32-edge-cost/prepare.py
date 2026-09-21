from pathlib import Path
import subprocess,shutil
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent;out=Path('/tmp/c32-edge-cost');out.mkdir(exist_ok=True)
s=subprocess.check_output(['git','show','8bca0f7:hip/c32_fused_ffn_attention.hip'],cwd=root,text=True)
a=s.index('template<bool HalfOutput,bool Mapped=false');b=s.index('\nKERNEL ',a);body=s[a:b]
code='#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n'+s+'\n'
for phase in ['input','tail']:
 t=body
 if phase=='input':
  a=t.index(' if constexpr(Prefix){uint l=tid%32;');b=t.index('\n#elif HIP_C32_INPUT_DWORD',a)
  part=t[a:b]
  # pre_acc must reset for each prefix pass; all waves repeat the same count.
  t=t[:a]+' _Pragma("clang loop unroll(disable)") for(uint rep=0;rep<probe_repeats;rep++){asm volatile("" ::: "memory");pre_acc[0]=f8{};pre_acc[1]=f8{};\n'+part+'\n asm volatile("" ::: "memory");sync_window();}\n'+t[b:]
 else:
  a=t.index(' if constexpr(Finish){\n  // c32_finish');b=t.rfind('\n}')
  t=t[:a]+' _Pragma("clang loop unroll(disable)") for(uint rep=0;rep<probe_repeats;rep++){asm volatile("" ::: "memory");\n'+t[a:b]+'\n asm volatile("" ::: "memory");}\n'+t[b:]
 t=t.replace('c32_fused_body(',f'c32_probe_{phase}_body(',1).replace(' uint window=bid();',' uint probe_repeats=windows>>28;windows&=0x0fffffffu;if(!probe_repeats)probe_repeats=1;\n uint window=bid();',1)
 code+=t+'\n';(here/(phase+'-body.inc')).write_text(t.rstrip()+'\n')
 for name in ['c32_fast_ffn_attention_fused_half_prefix_finish_main8','c32_fast_ffn_attention_fused_half_chain','c32_post_merge_head_half']:
  a=s.index('void '+name+'(');b=s.index('\n',a)
  line=s[a:b].replace('void '+name+'(', 'void '+name+'_probe_'+phase+'(',1).replace('c32_fused_body<',f'c32_probe_{phase}_body<')
  code+='KERNEL __attribute__((amdgpu_flat_work_group_size(128,128))) C32_OCC\n'+line+'\n'
(out/'kernel.hip').write_text(code)
(out/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (root/'Development/HIP').glob('*.h'):shutil.copyfile(p,out/'Development/HIP'/p.name)
p=out/'Development/HIP/hip_reference_network.h';s=p.read_text().replace('class Network {','class Network {\n bool c32_probe_done=false;',1)
needle='for(unsigned repeat=0;repeat<repeats_here;repeat++)api.Check(';assert s.count(needle)==1
s=s.replace(needle,(here/'timing.inc').read_text()+needle,1).replace(' Handle Stream()const{return stream;}',' bool C32ProbeDone()const{return c32_probe_done;}\n Handle Stream()const{return stream;}',1);p.write_text(s)
x=(root/'src/native_hip_network.h').read_text();a=x.index('hip_reference::Options o;');b=x.index('  const wchar_t*modules=',a)
opts=x[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift','o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)','o.assets=argv[1]')
(out/'pure.cpp').write_text((here/'runner.cpp.in').read_text().replace('/* OPTIONS */',opts))
