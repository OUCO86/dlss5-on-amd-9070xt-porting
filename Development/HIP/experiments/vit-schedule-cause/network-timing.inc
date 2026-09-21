 FILE*csv=fopen("network.csv","wb");if(!csv)throw std::runtime_error("csv");fprintf(csv,"variant,slot,mode,frames,mean_ms,bitdiff,replacements,start_ms,end_ms\n");
 for(unsigned variant=1;variant<=2;variant++)for(unsigned slot=0;slot<8;slot++){
  unsigned mode=(slot%4==1||slot%4==2)?variant:0;net.SetSchedule(mode);
  for(unsigned i=0;i<40;i++){net.Enqueue(x,nullptr,y,0);net.Synchronize();}
  net.SetSchedule(mode);auto tick=GetTickCount64();auto start=std::chrono::steady_clock::now();
  for(unsigned i=0;i<100;i++){net.Enqueue(x,nullptr,y,0);net.Synchronize();}
  double ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count()/100;auto end=GetTickCount64();
  std::vector<float>actual(expected.size());api.Check(api.hipMemcpy(actual.data(),y,actual.size()*4,2),"raw check");size_t diff=0;for(size_t i=0;i<actual.size();i++)diff+=memcmp(&actual[i],&expected[i],4)!=0;
  unsigned replaced=net.ScheduleReplaced();if(diff||(mode&&replaced!=800)||(!mode&&replaced))throw std::runtime_error("network output/replacement count");
  fprintf(csv,"%u,%u,%u,100,%.9f,%llu,%u,%llu,%llu\n",variant,slot,mode,ms,(unsigned long long)diff,replaced,(unsigned long long)tick,(unsigned long long)end);fflush(csv);printf("NETWORK mode=%u slot=%u ms=%.6f bitdiff=%llu replaced=%u\n",mode,slot,ms,(unsigned long long)diff,replaced);fflush(stdout);
 }
 fclose(csv);
