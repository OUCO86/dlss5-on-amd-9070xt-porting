from pathlib import Path
import shutil
here=Path(__file__).resolve().parent;root=here.parents[3];out=Path('/tmp/vit-eight-accumulators/network');out.mkdir(parents=True,exist_ok=True)
(out/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (root/'Development/HIP').glob('*.h'):shutil.copyfile(p,out/'Development/HIP'/p.name)
p=out/'Development/HIP/hip_reference_network.h';s=p.read_text().replace('class Network {','class Network {\n unsigned schedule_mode=0;unsigned schedule_replaced=0;',1)
needle='for(unsigned repeat=0;repeat<repeats_here;repeat++)api.Check('
insert='''if(schedule_mode&&kernel=="vit_pack_input"){kernel="vit_pack_input_tiled";schedule_replaced++;}else if(schedule_mode&&kernel=="vit_expand_blocked_fp8_frag_bytein"){kernel=schedule_mode==1?"probe_m32n64_tile":"probe_m32n64_tile_u2";U tokens;std::memcpy(&tokens,argv[3],sizeof(tokens));groups=((tokens+31)/32)*64;schedule_replaced++;}'''
assert s.count(needle)==1;s=s.replace(needle,insert+needle,1).replace(' Handle Stream()const{return stream;}',' void SetSchedule(unsigned n){schedule_mode=n;schedule_replaced=0;}\n unsigned ScheduleReplaced()const{return schedule_replaced;}\n Handle Stream()const{return stream;}',1);p.write_text(s)
x=(root/'src/native_hip_network.h').read_text();a=x.index('hip_reference::Options o;');b=x.index('  const wchar_t*modules=',a)
opts=x[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift','o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)','o.assets=argv[1]')
s=(root/'Development/HIP/experiments/vit-schedule-cause/runner.cpp.in').read_text();a=s.index(' for(unsigned frame=0;');b=s.index('api.hipFree(x);',a)
t=(root/'Development/HIP/experiments/vit-schedule-cause/network-timing.inc').read_text().replace('i<100','i<200').replace('.count()/100','.count()/200').replace('replaced!=800','replaced!=3200').replace(',100,',',200,')
s=s[:a]+t+s[b:];(out/'network.cpp').write_text(s.replace('/* OPTIONS */',opts).replace('PASS ViT schedule controls','PASS layout network controls'))
