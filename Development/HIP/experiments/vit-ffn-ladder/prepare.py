from pathlib import Path
import subprocess,shutil
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent;out=Path('/tmp/vit-ffn-ladder');out.mkdir(exist_ok=True)
s=subprocess.check_output(['git','show','8bca0f7:hip/deep_fast.hip'],cwd=root,text=True)
a=s.index('template<bool Tiled=false,bool ByteInput=false,bool Frag=false,bool TiledInput=false>');b=s.index('\n// BM token tiles',a);expand=s[a:b]
a=s.index('template<bool Partial,bool Tiled=false,bool ByteStream=false,bool HalfOut=false,bool Frag=false>');b=s.index('\n// Fragment-weight twin',a);contract=s[a:b]
code='#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_BRANCHLESS_F 1\n'+s+'\n'
for phase in ['raw','act']:
 t=expand.replace('vit_expand_blocked_body(',f'vit_expand_{phase}_body(',1)
 a=t.index(' for(uint n=0;n<4;n++)for(uint e=0;e<8;e++){float v=accum[n][e]')
 expr='accum[n][e]' if phase=='raw' else 'v*poly'
 prefix='' if phase=='raw' else 'float v=accum[n][e],g=clampf(v,-4.f,4.f),poly=__builtin_fmaf(g,absf(g)*(-.055908203125f)+.447265625f,.89453125f);'
 t=t[:a]+' for(uint n=0;n<4;n++)for(uint e=0;e<8;e++){'+prefix+'out[(first+gr()*8+e)*outputs+col+n*16+rc()]='+expr+';}\n}\n'
 code+=t+f'WAVE void ladder_expand_{phase}(const float*in,const float*w,float*out,uint tokens,uint inputs,uint outputs,const uint*gate){{vit_expand_{phase}_body<true,true,true>(in,w,out,tokens,inputs,outputs);}}\n'
t=contract.replace('vit_contract_blocked_body(','vit_contract_raw_body(',1)
a=t.index(' if constexpr(!Partial)for(uint n=0;n<4;n++)for(uint e=0;e<8;e++){uint i=')
t=t[:a]+' for(uint n=0;n<4;n++)for(uint e=0;e<8;e++)out[(first+gr()*8+e)*1024+col+n*16+rc()]=total[n][e];\n}\n'
code+=t+'WAVE void ladder_contract_raw(const float*in,const float*w,const float*skip,float*out,uint tokens,uint inputs,uint outputs,const uint*gate){vit_contract_raw_body<false,false,false,false,true>(in,w,skip,out,tokens); }\n'
code+='KERNEL __attribute__((amdgpu_flat_work_group_size(256,256)))\nvoid ladder_epilogue(const float*raw,float*out,uint count,uint mode){uint i=bid()*256+__builtin_amdgcn_workitem_id_x();if(i>=count)return;float v=raw[i];if(mode==0){float g=clampf(v,-4.f,4.f),p=__builtin_fmaf(g,absf(g)*(-.055908203125f)+.447265625f,.89453125f);reinterpret_cast<unsigned char*>(out)[i]=byte_F(v*p);}else if(mode==1)reinterpret_cast<unsigned char*>(out)[i]=byte_F(v);else out[i]=F(H(v));}\n'
(out/'kernel.hip').write_text(code)
(out/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (root/'Development/HIP').glob('*.h'):shutil.copyfile(p,out/'Development/HIP'/p.name)
p=out/'Development/HIP/hip_reference_network.h';s=p.read_text().replace('class Network {','class Network {\n bool c32_probe_done=false;',1)
needle='for(unsigned repeat=0;repeat<repeats_here;repeat++)api.Check(';assert s.count(needle)==1
s=s.replace(needle,(here/'timing.inc').read_text()+needle,1).replace(' Handle Stream()const{return stream;}',' bool C32ProbeDone()const{return c32_probe_done;}\n Handle Stream()const{return stream;}',1);p.write_text(s)
x=(root/'src/native_hip_network.h').read_text();a=x.index('hip_reference::Options o;');b=x.index('  const wchar_t*modules=',a)
opts=x[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift','o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)','o.assets=argv[1]')
(out/'pure.cpp').write_text((here/'runner.cpp.in').read_text().replace('/* OPTIONS */',opts))
