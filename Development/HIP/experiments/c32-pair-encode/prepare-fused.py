from pathlib import Path
import shutil
here=Path(__file__).resolve().parent;root=here.parents[3];out=Path('/tmp/c32-pair-encode/fused');(out/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (root/'Development/HIP').glob('*.h'):shutil.copyfile(p,out/'Development/HIP'/p.name)
p=out/'Development/HIP/hip_reference_network.h';s=p.read_text().replace('class Network {','class Network {\n bool c32_probe_done=false;',1)
needle='for(unsigned repeat=0;repeat<repeats_here;repeat++)api.Check(';assert s.count(needle)==1
s=s.replace(needle,(here/'fused-timing.inc').read_text()+needle,1).replace(' Handle Stream()const{return stream;}',' bool C32ProbeDone()const{return c32_probe_done;}\n Handle Stream()const{return stream;}',1);p.write_text(s)
x=(root/'src/native_hip_network.h').read_text();a=x.index('hip_reference::Options o;');b=x.index('  const wchar_t*modules=',a)
opts=x[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift','o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)','o.assets=argv[1]')
s=(root/'Development/HIP/experiments/c32-phase-cost/runner.cpp.in').read_text()
(out/'fused.cpp').write_text(s.replace('/* OPTIONS */',opts))
