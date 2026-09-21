from pathlib import Path
import subprocess,shutil
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent;out=Path('/tmp/vit-gap-controls');out.mkdir(exist_ok=True)
s=subprocess.check_output(['git','show','70656f8:hip/deep_fast.hip'],cwd=root,text=True)
a=s.index('template<bool Tiled=false,bool ByteInput=false,bool Frag=false,bool TiledInput=false>');b=s.index('\n// BM token tiles',a);expand=s[a:b]
a=s.index('template<bool Partial,bool Tiled=false,bool ByteStream=false,bool HalfOut=false,bool Frag=false>');b=s.index('\n// Fragment-weight twin',a);contract=s[a:b]
code='#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_BRANCHLESS_F 1\n'+s+'\n'
for name,unroll,warps,order in [('u1',1,1,False),('u2',2,1,False),('u4',4,1,False),('u8',8,1,False),('u16',16,1,False),('group4',4,4,False),('group8',4,8,False),('nmajor',4,1,True),('token_fixed',4,1,False)]:
 t=expand.replace('vit_expand_blocked_body(',f'gap_{name}_body(',1)
 t=t.replace(' for(uint k=0;k<inputs;k+=16)',f' _Pragma("unroll {unroll}") for(uint k=0;k<inputs;k+=16)')
 if warps>1:t=t.replace('bid()',f'(bid()*{warps}+__builtin_amdgcn_workitem_id_x()/32)')
 if order:t=t.replace('first=bid()/tiles*16,col=bid()%tiles*64','first=bid()%(tokens/16)*16,col=bid()/(tokens/16)*64')
 code+=t+'\n'
 sig=f'KERNEL __attribute__((amdgpu_flat_work_group_size({32*warps},{32*warps}))) void probe_{name}(const float*in,const float*w,float*out,uint tokens,uint inputs,uint outputs,const uint*gate)'
 call=f'gap_{name}_body<true,true,true>'
 if name in ('nmajor','token_fixed'):body=f'if(tokens==400){call}(in,w,out,400,1024,4096);else if(tokens==640){call}(in,w,out,640,1024,4096);'
 else:body=f'{call}(in,w,out,tokens,1024,4096);'
 code+=sig+'{if(gate&&gate[0])return;'+body+'}\n'
code+='WAVE void probe_m2(const float*in,const float*w,float*out,uint tokens,uint inputs,uint outputs,const uint*gate){if(gate&&gate[0])return;vit_expand_blocked_body_m<true,true,2,true>(in,w,out,tokens,1024,4096); }\n'
(out/'kernel.hip').write_text(code)
(out/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (root/'Development/HIP').glob('*.h'):shutil.copyfile(p,out/'Development/HIP'/p.name)
p=out/'Development/HIP/hip_reference_network.h';s=p.read_text().replace('class Network {','class Network {\n bool c32_probe_done=false;',1)
needle='for(unsigned repeat=0;repeat<repeats_here;repeat++)api.Check(';assert s.count(needle)==1
s=s.replace(needle,(here/'timing.inc').read_text()+needle,1).replace(' Handle Stream()const{return stream;}',' bool C32ProbeDone()const{return c32_probe_done;}\n Handle Stream()const{return stream;}',1);p.write_text(s)
x=(root/'src/native_hip_network.h').read_text();a=x.index('hip_reference::Options o;');b=x.index('  const wchar_t*modules=',a)
opts=x[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift','o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)','o.assets=argv[1]')
(out/'pure.cpp').write_text((here/'runner.cpp.in').read_text().replace('/* OPTIONS */',opts))
