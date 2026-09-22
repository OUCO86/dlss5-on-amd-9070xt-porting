from pathlib import Path
import shutil
here=Path(__file__).resolve().parent;root=here.parents[3];out=Path('/tmp/vit-repeat-context');out.mkdir(exist_ok=True)
(out/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (root/'Development/HIP').glob('*.h'):shutil.copyfile(p,out/'Development/HIP'/p.name)
p=out/'Development/HIP/hip_reference_network.h';s=p.read_text().replace('class Network {','class Network {\n'+(here/'members.inc').read_text(),1)
old='for(unsigned repeat=0;repeat<repeats_here;repeat++)api.Check(api.hipModuleLaunchKernel(Fn(module,kernel),groups?groups:(count+255ull)/256,1,1,threads,1,1,0,stream,argv,nullptr),name);'
assert s.count(old)==1;s=s.replace(old,(here/'dispatch.inc').read_text(),1)
s=s.replace(' Handle Stream()const{return stream;}',(here/'public.inc').read_text()+'\n Handle Stream()const{return stream;}',1);p.write_text(s)
x=(root/'src/native_hip_network.h').read_text();a=x.index('hip_reference::Options o;');b=x.index('  const wchar_t*modules=',a)
opts=x[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift','o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)','o.assets=argv[1]')
s=(root/'Development/HIP/experiments/vit-schedule-cause/runner.cpp.in').read_text();a=s.index(' for(unsigned frame=0;');b=s.index('api.hipFree(x);',a);s=s[:a]+(here/'timing.inc').read_text()+s[b:]
s=s.replace(' if(!net.C32ProbeDone())throw std::runtime_error("target not reached");','');(out/'network.cpp').write_text(s.replace('/* OPTIONS */',opts).replace('PASS ViT schedule controls','PASS ViT repeated pairs in real network'))
