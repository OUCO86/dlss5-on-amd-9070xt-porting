from pathlib import Path
import shutil
h=Path(__file__).resolve().parent;root=h.parents[3];out=Path('/tmp/wmma-pitch-gap/real');(out/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (root/'Development/HIP').glob('*.h'):shutil.copyfile(p,out/'Development/HIP'/p.name)
p=out/'Development/HIP/hip_reference_network.h';s=p.read_text().replace('class Network {','class Network {\n bool gap_captured=false;',1);needle='for(unsigned repeat=0;repeat<repeats_here;repeat++)api.Check(';assert s.count(needle)==1
s=s.replace(needle,'if(!gap_captured&&kernel=="vit_expand_blocked_fp8_frag_bytein"){gap_captured=true;repeats_here=10000;printf("REAL_TARGET %s repeats=%u\\n",kernel.c_str(),repeats_here);fflush(stdout);}\n '+needle,1)
s=s.replace(' Handle Stream()const{return stream;}',' bool C32ProbeDone()const{return gap_captured;}\n Handle Stream()const{return stream;}',1);p.write_text(s)
x=(root/'src/native_hip_network.h').read_text();a=x.index('hip_reference::Options o;');b=x.index('  const wchar_t*modules=',a);opts=x[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift','o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)','o.assets=argv[1]')
s=(root/'Development/HIP/experiments/c32-phase-cost/runner.cpp.in').read_text().replace('/* OPTIONS */',opts)
s=s.replace('for(unsigned frame=0;frame<2;frame++)','unsigned frames=std::getenv("GPU_GAP_CAPTURE")?1000u:2u;for(unsigned frame=0;frame<frames;frame++)').replace('net.Synchronize();std::vector<float>actual','net.Synchronize();if(frame!=0&&frame+1!=frames)continue;std::vector<float>actual').replace('PASS C32 phase controls','PASS real ViT capture control')
(out/'real.cpp').write_text(s)
