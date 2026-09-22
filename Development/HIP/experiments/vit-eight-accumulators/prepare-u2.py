from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent;out=Path('/tmp/vit-eight-u2');out.mkdir(exist_ok=True)
s=Path('/tmp/vit-eight-accumulators/kernel.hip').read_text();a=s.index('template<uint BM>\nDEV void eight_');extra=s[a:].replace('#pragma unroll 4','#pragma unroll 2')
for name in ['m16n128_row','m16n128_tile','m32n64_row','m32n64_tile']:extra=extra.replace(name,name+'_u2')
(out/'kernel.hip').write_text(s+'\n'+extra)
(out/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (root/'Development/HIP').glob('*.h'):shutil.copyfile(p,out/'Development/HIP'/p.name)
p=out/'Development/HIP/hip_reference_network.h';s=p.read_text().replace('class Network {','class Network {\n bool c32_probe_done=false;void*layout_float_input=nullptr;U layout_count=0;',1)
needle='for(unsigned repeat=0;repeat<repeats_here;repeat++)api.Check(';s=s.replace(needle,(here/'u2-timing.inc').read_text()+needle,1).replace(' Handle Stream()const{return stream;}',' bool C32ProbeDone()const{return c32_probe_done;}\n Handle Stream()const{return stream;}',1);p.write_text(s)
(out/'pure.cpp').write_text(Path('/tmp/vit-eight-accumulators/pure.cpp').read_text())
