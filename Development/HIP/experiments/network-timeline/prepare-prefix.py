from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent;out=Path('/tmp/network-prefix');out.mkdir(exist_ok=True)
(out/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (root/'Development/HIP').glob('*.h'):shutil.copyfile(p,out/'Development/HIP'/p.name)
p=out/'Development/HIP/hip_reference_network.h';s=p.read_text().replace('class Network {','class Network {\n'+(here/'prefix-members.inc').read_text(),1)
needle='if(opt.profile)api.Check(api.hipEventRecord(timing.end,stream),"event end");';assert s.count(needle)==1
s=s.replace(needle,'if(prefix_active){++prefix_cursor;if(prefix_cursor==234)api.Check(api.hipEventRecord(prefix_end,stream),"compute end marker");else if(prefix_cursor==prefix_cut)api.Check(api.hipEventRecord(prefix_mid,stream),"cut marker");}'+needle,1)
needle=' Handle Stream()const{return stream;}';assert s.count(needle)==1
s=s.replace(needle,(here/'prefix-public.inc').read_text()+needle,1);p.write_text(s)
s=(here/'runner.cpp.in').read_text();a=s.index(' net.ProbePrepare(');b=s.index('\n}catch(',a)
s=s[:a]+''' net.PrefixPrepare();
 FILE*base=fopen("prefix-baseline.csv","wb"),*cuts=fopen("prefix.csv","wb");if(!base||!cuts)throw std::runtime_error("CSV");fprintf(base,"phase,frame,wall_ms\\n");fprintf(cuts,"region,round,slot,cut,start_tick,end_tick,prefix_ms,gpu_frame_ms,tail_ms,wall_ms\\n");
 for(int i=0;i<60;i++)run();verify("warm-prefix");
 auto baseline=[&](unsigned phase){for(unsigned i=0;i<100;i++){auto t=std::chrono::steady_clock::now();run();fprintf(base,"%u,%u,%.9f\\n",phase,i,std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-t).count());}fflush(base);};baseline(0);
 unsigned boundaries[]={0,1,5,14,27,44,101,103,152,154,189,206,219,228,233,234};
 for(unsigned region=0;region<15;region++){
  for(unsigned i=0;i<8;i++)run();
  for(unsigned round=0;round<8;round++)for(unsigned slot=0;slot<4;slot++){
   unsigned cut=boundaries[region+((slot==1||slot==2)?1:0)];auto tick=GetTickCount64();auto t=std::chrono::steady_clock::now();
   net.PrefixBegin(cut);net.Enqueue(x,nullptr,y,0);net.PrefixEnd();net.Synchronize();double wall=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-t).count();auto stop=GetTickCount64();float prefix=0,whole=0,tail=0;net.PrefixRead(prefix,whole,tail);
   if(whole>wall+.05)throw std::runtime_error("GPU time exceeds wall");
   fprintf(cuts,"%u,%u,%u,%u,%llu,%llu,%.9f,%.9f,%.9f,%.9f\\n",region,round,slot,cut,tick,stop,double(prefix),double(whole),double(tail),wall);
  }
  fflush(cuts);verify(("prefix-region-"+std::to_string(region)).c_str());
 }
 baseline(1);verify("prefix-final");fclose(base);fclose(cuts);net.PrefixRelease();api.hipFree(x);api.hipFree(y);puts("PASS sparse prefix controls");return 0;
'''+s[b:]
x=(root/'src/native_hip_network.h').read_text();a=x.index('hip_reference::Options o;');b=x.index('  const wchar_t*modules=',a)
opts=x[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift','o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)','o.assets=argv[1]')
(out/'pure.cpp').write_text(s.replace('/* OPTIONS */',opts))
