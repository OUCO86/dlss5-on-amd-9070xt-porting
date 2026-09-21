from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent;out=Path('/tmp/vit-schedule-cause/network');out.mkdir(parents=True,exist_ok=True)
(out/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (root/'Development/HIP').glob('*.h'):shutil.copyfile(p,out/'Development/HIP'/p.name)
p=out/'Development/HIP/hip_reference_network.h';s=p.read_text().replace('class Network {','class Network {\n unsigned schedule_mode=0;unsigned schedule_replaced=0;',1)
needle='for(unsigned repeat=0;repeat<repeats_here;repeat++)api.Check('
insert='''if(schedule_mode==1&&kernel=="vit_expand_blocked_fp8_frag_bytein"){kernel="probe_expand_fixed";schedule_replaced++;}else if(schedule_mode==2&&kernel=="vit_contract_blocked_fp8_frag"){kernel="probe_contract_roll";schedule_replaced++;}'''
assert s.count(needle)==1;s=s.replace(needle,insert+needle,1).replace(' Handle Stream()const{return stream;}',' void SetSchedule(unsigned n){schedule_mode=n;schedule_replaced=0;}\n unsigned ScheduleReplaced()const{return schedule_replaced;}\n Handle Stream()const{return stream;}',1);p.write_text(s)
x=(root/'src/native_hip_network.h').read_text();a=x.index('hip_reference::Options o;');b=x.index('  const wchar_t*modules=',a)
opts=x[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift','o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)','o.assets=argv[1]')
s=(here/'runner.cpp.in').read_text();a=s.index(' for(unsigned frame=0;');b=s.index('api.hipFree(x);',a)
s=s[:a]+(here/'network-timing.inc').read_text()+s[b:];s=s.replace('/* OPTIONS */',opts).replace('PASS ViT schedule controls','PASS whole network schedule controls');(out/'network.cpp').write_text(s)
