from pathlib import Path
import subprocess
here=Path(__file__).resolve().parent;root=here.parents[3];out=Path('/tmp/vit-compute-density')
s=subprocess.check_output(['git','show','b2df1a5:hip/deep_fast.hip'],cwd=root,text=True)
a=s.index('template<bool Tiled=false,bool ByteInput=false,bool Frag=false,bool TiledInput=false>');b=s.index('\n// BM token tiles',a);expand=s[a:b]
code='#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_BRANCHLESS_F 1\n'+s+'\n'
for kind,repeats in [('work',1),('work',2),('work',4),('work',8),('control',2),('control',4),('control',8)]:
 name=f'{kind}{repeats}';t=expand.replace('vit_expand_blocked_body(',f'density_{name}_body(',1)
 t=t.replace(' for(uint k=0;k<inputs;k+=16)',' _Pragma("unroll 4") for(uint k=0;k<inputs;k+=16)')
 a=t.index('  for(uint n=0;n<4;n++){uint row=col+n*16+rc();i2 b;');b=t.index('\n }\n for(uint n=0;n<4;n++)for(uint e=0;e<8;e++){float v=accum',a)
 part='  i2 bs[4]; _Pragma("unroll 4") for(uint n=0;n<4;n++)bs[n]=vit_weight_fragment_native(w,col+n*16+rc(),inputs,k);\n'
 part+=f' _Pragma("unroll {repeats}") for(uint repeat=1;repeat<{repeats};repeat++){{f8 seed;_Pragma("unroll 8") for(uint e=0;e<8;e++)seed[e]=float(repeat*8+e+1)*.0625f; _Pragma("unroll 4") for(uint n=0;n<4;n++){{'
 if kind=='work':part+='f8 extra=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,bs[n],seed);'
 else:part+='f8 extra=seed;'
 part+='asm volatile("" : : '+','.join(f'"v"(extra[{e}])' for e in range(8))+');}}\n'
 part+=' _Pragma("unroll 4") for(uint n=0;n<4;n++)accum[n]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,bs[n],accum[n]);'
 t=t[:a]+part+t[b:];code+=t+'\n'
 code+=f'WAVE void probe_{name}(const float*in,const float*w,float*out,uint tokens,uint inputs,uint outputs,const uint*gate){{if(gate&&gate[0])return;density_{name}_body<true,true,true>(in,w,out,tokens,1024,4096);}}\n'
(out/'seeded.hip').write_text(code)
