from pathlib import Path
import subprocess,shutil,difflib
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent;out=Path('/tmp/c32-phase-cost');out.mkdir(exist_ok=True)
s=subprocess.check_output(['git','show','cd54a28:hip/c32_fused_ffn_attention.hip'],cwd=root,text=True)
a=s.index('template<bool HalfOutput,bool Mapped=false');b=s.index('\nKERNEL ',a);original=s[a:b]
def wrap(t,begin,end,init='',consume='',index=0):
 a=t.index(begin,index);b=t.index(end,a);part=t[a:b]
 return t[:a]+' _Pragma("clang loop unroll(disable)") for(uint probe_it=0;probe_it<probe_repeats;probe_it++){asm volatile("" ::: "memory");\n'+init+part+'\n'+consume+'asm volatile("" ::: "memory");}\n'+t[b:]
def consume(vs):return ''.join('asm volatile("" : : "v"('+v+') : "memory");' for v in vs)
variants={}
# 0: FFN dot products plus the original residual initialization (no extra seed buffer).
t=wrap(original,'  for(uint kt=0;kt<2;kt++){i2 a{},b{};uint k=kt*16+gr()*8;a=load8(packed+', '\n  for(uint e=0;e<8;e++){float v=sum[e]', 'sum=f8{};\n',consume([f'sum[{e}]' for e in range(8)]))
a=t.index(' f8 acc[2];');t=t[:a]+t[a:].replace(' f8 acc[2];acc[0]=f8{};acc[1]=f8{};', ' f8 acc[2];\n',1)
t=wrap(t,' if(residual_mode==0){','\n#if HIP_C32_ALIAS_FFN_V && HIP_C32_REGISTER_FFN', 'acc[0]=f8{};acc[1]=f8{};\n',consume([f'acc[{j}][{e}]' for j in range(2) for e in range(8)]),t.index(' f8 acc[2];'))
variants['ffn']=t
# 1: FFN activation/FP8 packing and the post-contraction RTZ/half/FP8 stores.
t=original;a=t.index('  for(uint e=0;e<8;e++){float v=sum[e]');b=t.index('\n }\n#endif',a)
part=t[a:b].replace('float v=sum[e],g=', 'float v=sum[e];asm volatile("" : "+v"(v) : : "memory");float g=')
t=t[:a]+' _Pragma("clang loop unroll(disable)") for(uint probe_it=0;probe_it<probe_repeats;probe_it++){\n _Pragma("unroll 8")\n'+part+'\nasm volatile("" ::: "memory");}\n'+t[b:]
a=t.index(' for(uint ci=0;ci<2;ci++)for(uint e=0;e<8;e++){',t.index('#if HIP_C32_ALIAS_FFN_V && HIP_C32_REGISTER_FFN'));b=t.index('\n sync_window();\n // A single raw QKV',a)
part=t[a:b].replace('float v=Hrtz(acc[ci][e]);','float source=acc[ci][e];asm volatile("" : "+v"(source) : : "memory");float v=Hrtz(source);')
t=t[:a]+' _Pragma("clang loop unroll(disable)") for(uint probe_it=0;probe_it<probe_repeats;probe_it++){\n'+part+'\nasm volatile("" ::: "memory");}\n'+t[b:];variants['pack']=t.replace('for(uint ci=0;ci<2;ci++)for(uint e=0;e<8;e++){', '_Pragma("unroll 2") for(uint ci=0;ci<2;ci++) _Pragma("unroll 8") for(uint e=0;e<8;e++){')
# Encoding-only refinement: observe each encoded value through a register operand,
# rather than clobbering all memory after each pass. Repeated stores may sink;
# this probe measures activation/RTZ/FP8 arithmetic, not repeated LDS traffic.
t=variants['pack'].replace('asm volatile("" : "+v"(v) : : "memory");','asm volatile("" : "+v"(v));').replace('asm volatile("" : "+v"(source) : : "memory");','asm volatile("" : "+v"(source));')
t=t.replace('scratch.hidden[(first+gr()*8+e)*132+col+rc()]=static_cast<unsigned char>(fp8(v*p));','uint probe_byte=fp8(v*p);asm volatile("" : : "v"(probe_byte));scratch.hidden[(first+gr()*8+e)*132+col+rc()]=static_cast<unsigned char>(probe_byte);')
t=t.replace('ffn8[(first+gr()*8+e)*36+ci*16+rc()]=static_cast<unsigned char>(fp8(v));','uint probe_byte=fp8(v);asm volatile("" : : "v"(probe_byte));ffn8[(first+gr()*8+e)*36+ci*16+rc()]=static_cast<unsigned char>(probe_byte);')
t=t.replace('asm volatile("" ::: "memory");}\n','}\n')
variants['pack']=t
# 2: QKV matrices; pack/normalize after each completed repeated dot (FFN/V alias stays intact).
t=wrap(original,'   for(uint kt=0;kt<2;kt++){i2 a{},b{};','\n   for(uint e=0;e<8;e++)scratch.raw', 'acc=f8{};\n',consume([f'acc[{e}]' for e in range(8)]),original.index('// A single raw QKV'))
variants['qkv']=t
# 3: attention score matrix and bias/exponent encoding, Q/K remain intact until probability packing.
a=original.index(' _Pragma("unroll 4") for(uint key=0;key<64;key+=16){f8 acc{};');b=original.index('\n ATTN_SYNC();',a)
t=original[:a]+' _Pragma("clang loop unroll(disable)") for(uint probe_it=0;probe_it<probe_repeats;probe_it++){asm volatile("" ::: "memory");\n'+original[a:b]+'\nasm volatile("" ::: "memory");}\n'+original[b:];variants['scores']=t
# 4: Q/K normalization and QKV packing, plus probability normalization/packing. Production scratch alias mode only.
t=wrap(original,'f8 sum{};\n  if(part<2)', '\n  sync_owned_rows();\n }',index=original.index('// A single raw QKV'))
t=wrap(t,' {f8 sum{};for(uint kt=0;kt<4;kt++)', '\n ATTN_SYNC();\n // Both AV',index=t.index('// Scores no longer consume Q/K'))
variants['norm']=t.replace('C32_LOOP for(uint part=0;part<3;part++){', '_Pragma("unroll 3") for(uint part=0;part<3;part++){')
# 5: AV matrices; publish packed AV only after repeated dots finish.
t=wrap(original,'  for(uint kt=0;kt<4;kt++){i2 a{},b{};', 'av[ci]=acc;', 'acc=f8{};\n',consume([f'acc[{e}]' for e in range(8)]),original.index('// Both AV column fragments'))
variants['av']=t
# 6: attention projection, residual/RTZ and output staging (epilogue/head only once).
t=wrap(original,' C32_LOOP for(uint col=0;col<32;col+=16){f8 acc{};', '\n#endif\n\n if constexpr(Finish)',index=original.index('#if HIP_C32_ABLATE!=3'))
variants['project']=t
names=['c32_fast_ffn_attention_fused_half_prefix_finish_main8','c32_fast_ffn_attention_fused_half_chain','c32_post_merge_head_half']
code='#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n'+s+'\n#if HIP_C32_LOCAL_ATTN_SYNC\n#error phase probe requires production probability scratch layout\n#endif\n'
for phase,t in variants.items():
 t=t.replace('c32_fused_body(',f'c32_probe_{phase}_body(',1)
 needle=' uint window=bid();'
 assert t.count(needle)==1
 t=t.replace(needle,' uint probe_repeats=windows>>28;windows&=0x0fffffffu;if(!probe_repeats)probe_repeats=1;\n'+needle,1)
 code+='\n'+t+'\n'
 for name in names:
  a=s.index('void '+name+'(');b=s.index('\n',a);line=s[a:b]
  line=line.replace('void '+name+'(', 'void '+name+'_probe_'+phase+'(',1).replace('c32_fused_body<',f'c32_probe_{phase}_body<')
  code+='KERNEL __attribute__((amdgpu_flat_work_group_size(128,128))) C32_OCC\n'+line+'\n'
 (here/(phase+'.patch')).write_text(''.join(difflib.unified_diff(original.splitlines(True),t.splitlines(True),fromfile='original-body',tofile=phase+'-diagnostic-body',n=0)))
(out/'kernel.hip').write_text(code)
# Standalone pure-HIP host using current dimensions/options and validated captured input.
(out/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (root/'Development/HIP').glob('*.h'):shutil.copyfile(p,out/'Development/HIP'/p.name)
p=out/'Development/HIP/hip_reference_network.h';s=p.read_text().replace('class Network {','class Network {\n bool c32_probe_done=false;',1)
needle='for(unsigned repeat=0;repeat<repeats_here;repeat++)api.Check(';assert s.count(needle)==1
s=s.replace(needle,(here/'timing.inc').read_text()+needle,1)
s=s.replace(' Handle Stream()const{return stream;}',' bool C32ProbeDone()const{return c32_probe_done;}\n Handle Stream()const{return stream;}',1);p.write_text(s)
x=(root/'src/native_hip_network.h').read_text();a=x.index('hip_reference::Options o;');b=x.index('  const wchar_t*modules=',a)
opts=x[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift','o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)','o.assets=argv[1]')
(out/'pure.cpp').write_text((here/'runner.cpp.in').read_text().replace('/* OPTIONS */',opts))
print('generated',list(variants))
