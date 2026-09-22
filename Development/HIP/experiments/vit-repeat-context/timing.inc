 FILE*csv=fopen("repeat.csv","wb");if(!csv)throw std::runtime_error("csv");fprintf(csv,"test,slot,mode,repeats,frames,wall_ms,bitdiff,pairs,extra_pairs,expand_launches,replacements,start_ms,end_ms\n");
 for(const char*test:{"ab_r1","ab_r2","ab_r4","slope_base","slope_candidate"})for(unsigned slot=0;slot<8;slot++){
  bool b=slot%4==1||slot%4==2;std::string name=test;
  unsigned mode=name=="slope_base"?0:name=="slope_candidate"?1:unsigned(b);
  unsigned repeats=name=="ab_r1"?1:name=="ab_r2"?2:name=="ab_r4"?4:b?4:1;
  net.SetAmplification(mode,repeats);for(unsigned i=0;i<30;i++){net.Enqueue(x,nullptr,y,0);net.Synchronize();}
  net.SetAmplification(mode,repeats);const unsigned frames=120;auto tick=GetTickCount64();auto start=std::chrono::steady_clock::now();
  for(unsigned i=0;i<frames;i++){net.Enqueue(x,nullptr,y,0);net.Synchronize();}
  double ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count()/frames;auto end=GetTickCount64();
  std::vector<float>actual(expected.size());api.Check(api.hipMemcpy(actual.data(),y,actual.size()*4,2),"raw check");size_t diff=0;for(size_t i=0;i<actual.size();i++)diff+=memcmp(&actual[i],&expected[i],4)!=0;
  if(diff||net.AmpPairs()!=frames*8||net.AmpExtras()!=frames*8*(repeats-1)||net.AmpLaunches()!=frames*8*repeats||net.AmpReplaced()!=(mode?frames*16:0))throw std::runtime_error("output or dispatch count mismatch");
  fprintf(csv,"%s,%u,%u,%u,%u,%.9f,%llu,%u,%u,%u,%u,%llu,%llu\n",test,slot,mode,repeats,frames,ms,(unsigned long long)diff,net.AmpPairs(),net.AmpExtras(),net.AmpLaunches(),net.AmpReplaced(),(unsigned long long)tick,(unsigned long long)end);fflush(csv);
  printf("REPEAT %s slot=%u mode=%u R=%u wall=%.6f bitdiff=%llu\n",test,slot,mode,repeats,ms,(unsigned long long)diff);fflush(stdout);
 }fclose(csv);
