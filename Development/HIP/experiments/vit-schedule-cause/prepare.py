from pathlib import Path
import subprocess,shutil
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent;out=Path('/tmp/vit-schedule-cause');out.mkdir(exist_ok=True)
s=subprocess.check_output(['git','show','8bca0f7:hip/deep_fast.hip'],cwd=root,text=True)
a=s.index('template<bool Tiled=false,bool ByteInput=false,bool Frag=false,bool TiledInput=false>');b=s.index('\n// BM token tiles',a);expand=s[a:b]
a=s.index('template<bool Partial,bool Tiled=false,bool ByteStream=false,bool HalfOut=false,bool Frag=false>');b=s.index('\n// Fragment-weight twin',a);contract=s[a:b]
code='#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_BRANCHLESS_F 1\n'+s+'\n'
for name,kind,fixed,unroll in [('expand_fixed','expand',True,None),('expand_fixed_roll','expand',True,0),('expand_dynamic_u4','expand',False,4),('expand_fixed_u4','expand',True,4),('contract_roll','contract',True,0)]:
 t=expand if kind=='expand' else contract
 old='vit_expand_blocked_body' if kind=='expand' else 'vit_contract_blocked_body'
 t=t.replace(old,name+'_body')
 if unroll is not None:
  marker=' for(uint k=0;k<inputs;k+=16)' if kind=='expand' else '  for(uint k=part*1024;k<(part+1)*1024;k+=16)'
  assert t.count(marker)==1
  pragma='_Pragma("clang loop unroll(disable)")' if unroll==0 else '_Pragma("unroll 4")'
  t=t.replace(marker,' '+pragma+marker)
 code+=t+'\n'
 if kind=='expand':
  dims='1024,4096' if fixed else 'inputs,outputs'
  guard='if(inputs==1024&&outputs==4096)' if fixed else ''
  code+=f'WAVE void probe_{name}(const float*in,const float*w,float*out,uint tokens,uint inputs,uint outputs,const uint*gate){{if(gate&&gate[0])return;{guard}{name}_body<true,true,true>(in,w,out,tokens,{dims});}}\n'
 else:code+=f'WAVE void probe_{name}(const float*in,const float*w,const float*skip,float*out,uint tokens,uint inputs,uint outputs,const uint*gate){{if(gate&&gate[0])return;if(inputs==4096&&outputs==1024){name}_body<false,false,false,false,true>(in,w,skip,out,tokens);}}\n'
(out/'kernel.hip').write_text(code)
(out/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (root/'Development/HIP').glob('*.h'):shutil.copyfile(p,out/'Development/HIP'/p.name)
p=out/'Development/HIP/hip_reference_network.h';s=p.read_text().replace('class Network {','class Network {\n bool c32_probe_done=false;',1)
needle='for(unsigned repeat=0;repeat<repeats_here;repeat++)api.Check(';assert s.count(needle)==1
s=s.replace(needle,(here/'timing.inc').read_text()+needle,1).replace(' Handle Stream()const{return stream;}',' bool C32ProbeDone()const{return c32_probe_done;}\n Handle Stream()const{return stream;}',1);p.write_text(s)
x=(root/'src/native_hip_network.h').read_text();a=x.index('hip_reference::Options o;');b=x.index('  const wchar_t*modules=',a)
opts=x[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift','o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)','o.assets=argv[1]')
(out/'pure.cpp').write_text((here/'runner.cpp.in').read_text().replace('/* OPTIONS */',opts))
