 net.PreparePrefix();
 FILE*csv=fopen("prefix.csv","wb"),*control=fopen("control.csv","wb");if(!csv||!control)throw std::runtime_error("csv");
 fprintf(csv,"slot,mode,round,edge,after,start_tick,end_tick,prefix_ms,whole_ms,tail_ms,wall_ms,valid\n");
 fprintf(control,"slot,mode,phase,frames,wall_ms,bitdiff,replacements,start_tick,end_tick\n");
 auto verify=[&](){std::vector<float>actual(expected.size());api.Check(api.hipMemcpy(actual.data(),y,actual.size()*4,2),"raw check");size_t diff=0;for(size_t i=0;i<actual.size();i++)diff+=memcmp(&actual[i],&expected[i],4)!=0;if(diff)throw std::runtime_error("network output changed");return diff;};
 for(unsigned slot=0;slot<8;slot++){
  unsigned mode=slot%4==1||slot%4==2;net.SetSchedule(mode);
  auto run=[&](){net.Enqueue(x,nullptr,y,0);net.Synchronize();};
  for(unsigned i=0;i<30;i++)run();
  auto plain=[&](unsigned phase){net.SetSchedule(mode);auto tick=GetTickCount64();auto start=std::chrono::steady_clock::now();for(unsigned i=0;i<80;i++)run();double ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count()/80;auto end=GetTickCount64();auto diff=verify();if(net.ScheduleReplaced()!=(mode?1280u:0u))throw std::runtime_error("plain count");fprintf(control,"%u,%u,%u,80,%.9f,%llu,%u,%llu,%llu\n",slot,mode,phase,ms,(unsigned long long)diff,net.ScheduleReplaced(),(unsigned long long)tick,(unsigned long long)end);fflush(control);};
  plain(0);net.SetSchedule(mode);
  for(unsigned round=0;round<16;round++)for(unsigned edge=0;edge<4;edge++){
   bool after=edge==1||edge==2;auto tick=GetTickCount64();auto start=std::chrono::steady_clock::now();net.BeginPrefix(after);net.Enqueue(x,nullptr,y,0);net.EndPrefix();net.Synchronize();double wall=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();auto end=GetTickCount64();
   float prefix=0,whole=0,tail=0;net.ReadPrefix(prefix,whole,tail);bool valid=std::isfinite(prefix)&&std::isfinite(whole)&&std::isfinite(tail)&&prefix>0&&tail>0&&whole>0&&fabs(double(prefix)+tail-whole)<.00005&&whole<wall+.05;
   fprintf(csv,"%u,%u,%u,%u,%u,%llu,%llu,%.9f,%.9f,%.9f,%.9f,%u\n",slot,mode,round,edge,unsigned(after),(unsigned long long)tick,(unsigned long long)end,prefix,whole,tail,wall,unsigned(valid));fflush(csv);if(!valid)throw std::runtime_error("long prefix invalid; raw values saved");
  }
  if(net.ScheduleReplaced()!=(mode?1024u:0u))throw std::runtime_error("marked count");verify();plain(1);
  printf("PREFIX slot=%u mode=%u bitdiff=0\n",slot,mode);fflush(stdout);
 }
 net.ReleasePrefix();fclose(csv);fclose(control);
