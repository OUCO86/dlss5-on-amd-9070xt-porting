from pathlib import Path
import shutil
here=Path(__file__).resolve().parent;root=here.parents[3];out=Path('/tmp/vit-in-context');out.mkdir(exist_ok=True)
(out/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (root/'Development/HIP').glob('*.h'):shutil.copyfile(p,out/'Development/HIP'/p.name)
p=out/'Development/HIP/hip_reference_network.h';s=p.read_text().replace('class Network {','class Network {\n'+(here/'members.inc').read_text(),1)
needle='for(unsigned repeat=0;repeat<repeats_here;repeat++)api.Check('
insert='''bool context_start=kernel=="vit_pack_input"&&context_pack++==0;
 bool context_end=kernel=="vit_expand_blocked_fp8_frag_bytein"&&context_pack==1;
 if(schedule_mode&&kernel=="vit_pack_input"){kernel="vit_pack_input_tiled";schedule_replaced++;}
 else if(schedule_mode&&kernel=="vit_expand_blocked_fp8_frag_bytein"){kernel="probe_m32n64_tile_u2";U tokens;std::memcpy(&tokens,argv[3],sizeof(tokens));groups=((tokens+31)/32)*64;schedule_replaced++;}
 if(context_frame>=0&&context_start){auto&e=context_events[context_frame];api.Check(api.hipEventRecord(e.begin,stream),"context begin");e.began=true;}
'''
assert s.count(needle)==1;s=s.replace(needle,insert+needle,1)
needle='if(opt.profile)api.Check(api.hipEventRecord(timing.end,stream),"event end");'
s=s.replace(needle,'''if(context_frame>=0&&context_end){auto&e=context_events[context_frame];api.Check(api.hipEventRecord(e.end,stream),"context end");e.ended=true;}'''+needle,1)
s=s.replace(' Handle Stream()const{return stream;}',(here/'public.inc').read_text()+'\n Handle Stream()const{return stream;}',1);p.write_text(s)
x=(root/'src/native_hip_network.h').read_text();a=x.index('hip_reference::Options o;');b=x.index('  const wchar_t*modules=',a)
opts=x[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift','o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)','o.assets=argv[1]')
s=(root/'Development/HIP/experiments/vit-schedule-cause/runner.cpp.in').read_text();a=s.index(' for(unsigned frame=0;');b=s.index('api.hipFree(x);',a)
s=s[:a]+(here/'timing.inc').read_text()+s[b:];s=s.replace(' if(!net.C32ProbeDone())throw std::runtime_error("target not reached");','');(out/'network.cpp').write_text(s.replace('/* OPTIONS */',opts).replace('PASS ViT schedule controls','PASS ViT real-context timing'))
