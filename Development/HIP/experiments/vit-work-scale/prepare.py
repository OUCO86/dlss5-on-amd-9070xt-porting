from pathlib import Path
import subprocess,shutil
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent;out=Path('/tmp/vit-work-scale');out.mkdir(exist_ok=True)
s=subprocess.check_output(['git','show','11bc0ad:hip/deep_fast.hip'],cwd=root,text=True)
a=s.index('template<bool Tiled=false,bool ByteInput=false,bool Frag=false,bool TiledInput=false>');b=s.index('\n// BM token tiles',a);expand=s[a:b]
a=s.index('template<bool Partial,bool Tiled=false,bool ByteStream=false,bool HalfOut=false,bool Frag=false>');b=s.index('\n// Fragment-weight twin',a);contract=s[a:b]
code='#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_BRANCHLESS_F 1\n'+s+'\n'
a=s.index('template<bool Tiled,bool ByteInput,uint BM,bool Frag=false>');b=s.index('\nWAVE void vit_expand_blocked_fp8_tiled_bytein_m4',a);m2=s[a:b]
for bm,body in ((1,expand),(2,m2)):
 name=f'scale_m{bm}_body';old='vit_expand_blocked_body' if bm==1 else 'vit_expand_blocked_body_m'
 body=body.replace(old,name).replace('uint inputs,uint outputs)','uint inputs,uint outputs,uint logical_bid)').replace('bid()','logical_bid')
 if bm==1:body=body.replace(' for(uint k=0;k<inputs;k+=16)',' _Pragma("unroll 4") for(uint k=0;k<inputs;k+=16)')
 code+=body+'\n'
 code+=f'template<uint T,bool Interleave> DEV void scale_dispatch_m{bm}(const float*in,const float*w,float*out,uint copies){{constexpr uint per=((T+{16*bm-1})/{16*bm})*64;uint logical=Interleave?bid()/copies:bid()%per,copy=Interleave?bid()%copies:bid()/per;if(copy>=copies)return;float*dest=reinterpret_cast<float*>(reinterpret_cast<unsigned char*>(out)+copy*T*4096);{name}<true,true'+(',true>' if bm==1 else ',2,true>')+'(in,w,dest,T,1024,4096,logical); }\n'
 for order in ('major','interleave'):
  which='true' if order=='interleave' else 'false'
  code+=f'WAVE void probe_m{bm}_{order}(const float*in,const float*w,float*out,uint tokens,uint copies,uint outputs,const uint*gate){{if(gate&&gate[0])return;if(tokens==400)scale_dispatch_m{bm}<400,{which}>(in,w,out,copies);else if(tokens==640)scale_dispatch_m{bm}<640,{which}>(in,w,out,copies);}}\n'
(out/'kernel.hip').write_text(code)
(out/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (root/'Development/HIP').glob('*.h'):shutil.copyfile(p,out/'Development/HIP'/p.name)
p=out/'Development/HIP/hip_reference_network.h';s=p.read_text().replace('class Network {','class Network {\n bool c32_probe_done=false;',1)
needle='for(unsigned repeat=0;repeat<repeats_here;repeat++)api.Check(';assert s.count(needle)==1
s=s.replace(needle,(here/'timing.inc').read_text()+needle,1).replace(' Handle Stream()const{return stream;}',' bool C32ProbeDone()const{return c32_probe_done;}\n Handle Stream()const{return stream;}',1);p.write_text(s)
x=(root/'src/native_hip_network.h').read_text();a=x.index('hip_reference::Options o;');b=x.index('  const wchar_t*modules=',a)
opts=x[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift','o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)','o.assets=argv[1]')
(out/'pure.cpp').write_text((here/'runner.cpp.in').read_text().replace('/* OPTIONS */',opts))
