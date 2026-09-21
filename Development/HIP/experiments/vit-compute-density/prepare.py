from pathlib import Path
import subprocess,shutil
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent;out=Path('/tmp/vit-compute-density');out.mkdir(exist_ok=True)
s=subprocess.check_output(['git','show','b2df1a5:hip/deep_fast.hip'],cwd=root,text=True)
a=s.index('template<bool Tiled=false,bool ByteInput=false,bool Frag=false,bool TiledInput=false>');b=s.index('\n// BM token tiles',a);expand=s[a:b]
a=s.index('template<bool Partial,bool Tiled=false,bool ByteStream=false,bool HalfOut=false,bool Frag=false>');b=s.index('\n// Fragment-weight twin',a);contract=s[a:b]
code='#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_BRANCHLESS_F 1\n'+s+'\n'
for kind,repeats in [('work',1),('work',2),('work',4),('work',8),('control',2),('control',4),('control',8)]:
 name=f'{kind}{repeats}';t=expand.replace('vit_expand_blocked_body(',f'density_{name}_body(',1)
 t=t.replace(' for(uint k=0;k<inputs;k+=16)',' _Pragma("unroll 4") for(uint k=0;k<inputs;k+=16)')
 a=t.index('  for(uint n=0;n<4;n++){uint row=col+n*16+rc();i2 b;');b=t.index('\n }\n for(uint n=0;n<4;n++)for(uint e=0;e<8;e++){float v=accum',a)
 part='  i2 bs[4]; _Pragma("unroll 4") for(uint n=0;n<4;n++)bs[n]=vit_weight_fragment_native(w,col+n*16+rc(),inputs,k);\n'
 part+=f' _Pragma("unroll {repeats}") for(uint repeat=1;repeat<{repeats};repeat++){{ _Pragma("unroll 4") for(uint n=0;n<4;n++){{i2 opaque=bs[n];asm volatile("" : "+v"(opaque[0]),"+v"(opaque[1]));'
 if kind=='work':part+='f8 extra=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,opaque,f8{});asm volatile("" : : '+','.join(f'"v"(extra[{e}])' for e in range(8))+');'
 else:part+='asm volatile("" : : "v"(opaque[0]),"v"(opaque[1]));'
 part+='}}\n _Pragma("unroll 4") for(uint n=0;n<4;n++)accum[n]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,bs[n],accum[n]);'
 t=t[:a]+part+t[b:];code+=t+'\n'
 code+=f'WAVE void probe_{name}(const float*in,const float*w,float*out,uint tokens,uint inputs,uint outputs,const uint*gate){{if(gate&&gate[0])return;density_{name}_body<true,true,true>(in,w,out,tokens,1024,4096);}}\n'
(out/'kernel.hip').write_text(code)
(out/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (root/'Development/HIP').glob('*.h'):shutil.copyfile(p,out/'Development/HIP'/p.name)
p=out/'Development/HIP/hip_reference_network.h';s=p.read_text().replace('class Network {','class Network {\n bool c32_probe_done=false;',1)
needle='for(unsigned repeat=0;repeat<repeats_here;repeat++)api.Check(';assert s.count(needle)==1
s=s.replace(needle,(here/'timing.inc').read_text()+needle,1).replace(' Handle Stream()const{return stream;}',' bool C32ProbeDone()const{return c32_probe_done;}\n Handle Stream()const{return stream;}',1);p.write_text(s)
x=(root/'src/native_hip_network.h').read_text();a=x.index('hip_reference::Options o;');b=x.index('  const wchar_t*modules=',a)
opts=x[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift','o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)','o.assets=argv[1]')
(out/'pure.cpp').write_text((here/'runner.cpp.in').read_text().replace('/* OPTIONS */',opts))
