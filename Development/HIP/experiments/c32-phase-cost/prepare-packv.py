from pathlib import Path
import subprocess
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent;out=Path('/tmp/c32-phase-cost');out.mkdir(exist_ok=True)
s=subprocess.check_output(['git','show','cd54a28:hip/c32_fused_ffn_attention.hip'],cwd=root,text=True);a=s.index('template<bool HalfOutput,bool Mapped=false');b=s.index('\nKERNEL ',a);t=s[a:b]
def opaque(values):return 'asm volatile("" : '+','.join('"+v"('+v+')' for v in values)+');'
def observe(values):return 'asm volatile("" : : '+','.join('"v"('+v+')' for v in values)+');'
a=t.index('  for(uint e=0;e<8;e++){float v=sum[e]');b=t.index('\n }\n#endif',a)
part=''' _Pragma("clang loop unroll(disable)") for(uint rep=0;rep<probe_repeats;rep++){
  f8 values=sum;uint encoded[8];
'''+opaque([f'values[{e}]' for e in range(8)])+'''
  _Pragma("unroll 8") for(uint e=0;e<8;e++){float v=values[e],g=clampf(v,-4.f,4.f),q=absf(g)*(-.055908203125f)+.447265625f,p=g*q+.89453125f;encoded[e]=fp8(v*p);}
'''+observe([f'encoded[{e}]' for e in range(8)])+'''
  _Pragma("unroll 8") for(uint e=0;e<8;e++)scratch.hidden[(first+gr()*8+e)*132+col+rc()]=static_cast<unsigned char>(encoded[e]);
 }
'''
t=t[:a]+part+t[b:]
a=t.index(' for(uint ci=0;ci<2;ci++)for(uint e=0;e<8;e++){',t.index('#if HIP_C32_ALIAS_FFN_V && HIP_C32_REGISTER_FFN'));b=t.index('\n sync_window();\n // A single raw QKV',a)
part=''' _Pragma("clang loop unroll(disable)") for(uint rep=0;rep<probe_repeats;rep++){
  f8 values[2]={acc[0],acc[1]};uint encoded[2][8];
'''+opaque([f'values[0][{e}]' for e in range(8)])+opaque([f'values[1][{e}]' for e in range(8)])+'''
  _Pragma("unroll 2") for(uint ci=0;ci<2;ci++) _Pragma("unroll 8") for(uint e=0;e<8;e++){float v=Hrtz(values[ci][e]);saved_ffn[ci][e]=(_Float16)v;encoded[ci][e]=fp8(v);}
'''+observe([f'encoded[{ci}][{e}]' for ci in range(2) for e in range(8)])+'''
  _Pragma("unroll 2") for(uint ci=0;ci<2;ci++) _Pragma("unroll 8") for(uint e=0;e<8;e++)ffn8[(first+gr()*8+e)*36+ci*16+rc()]=static_cast<unsigned char>(encoded[ci][e]);
 }
'''
t=t[:a]+part+t[b:]
t=t.replace('c32_fused_body(', 'c32_probe_packv_body(',1).replace(' uint window=bid();',' uint probe_repeats=windows>>28;windows&=0x0fffffffu;if(!probe_repeats)probe_repeats=1;\n uint window=bid();',1)
code='#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n'+s+'\n#if !HIP_C32_REGISTER_FFN\n#error packv requires production register FFN\n#endif\n'+t+'\n'
for name in ['c32_fast_ffn_attention_fused_half_prefix_finish_main8','c32_fast_ffn_attention_fused_half_chain','c32_post_merge_head_half']:
 a=s.index('void '+name+'(');b=s.index('\n',a);line=s[a:b].replace('void '+name+'(', 'void '+name+'_probe_packv(',1).replace('c32_fused_body<','c32_probe_packv_body<')
 code+='KERNEL __attribute__((amdgpu_flat_work_group_size(128,128))) C32_OCC\n'+line+'\n'
(out/'packv.hip').write_text(code);(here/'packv-body.inc').write_text(t.rstrip()+'\n')
