 FILE*csv=fopen("network.csv","wb");if(!csv)throw std::runtime_error("csv");fprintf(csv,"test,slot,mode,frames,wall_ms,bitdiff,calls,perframe,start_ms,end_ms\n");
 const unsigned ntests=std::getenv("DLSS5_PDL_TESTS")?unsigned(std::stoul(std::getenv("DLSS5_PDL_TESTS"))):4;for(unsigned test=1;test<=ntests;test++){unsigned perframe_ref=0;for(unsigned slot=0;slot<8;slot++){
  unsigned mode=(slot%4==1||slot%4==2)?test:0;
  net.SetPairMode(mode?mode:test);for(unsigned i=0;i<30;i++){net.Enqueue(x,nullptr,y,0);net.Synchronize();}
  unsigned perframe=net.PairCalls()/30;if(!perframe_ref)perframe_ref=perframe;if(perframe!=perframe_ref||perframe*30!=net.PairCalls())throw std::runtime_error("routed call count changed");
  net.SetPairMode(mode);const unsigned frames=160;auto tick=GetTickCount64();auto start=std::chrono::steady_clock::now();
  for(unsigned i=0;i<frames;i++){net.Enqueue(x,nullptr,y,0);net.Synchronize();}
  double ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count()/frames;auto end=GetTickCount64();
  std::vector<float>actual(expected.size());api.Check(api.hipMemcpy(actual.data(),y,actual.size()*4,2),"raw check");size_t diff=0;for(size_t i=0;i<actual.size();i++)diff+=memcmp(&actual[i],&expected[i],4)!=0;
  if(diff||(mode&&net.PairCalls()!=frames*perframe_ref)||(!mode&&net.PairCalls()!=0))throw std::runtime_error("output or dispatch mismatch");
  fprintf(csv,"%u,%u,%u,%u,%.9f,%llu,%u,%u,%llu,%llu\n",test,slot,mode,frames,ms,(unsigned long long)diff,net.PairCalls(),perframe_ref,(unsigned long long)tick,(unsigned long long)end);fflush(csv);
  printf("PAIR test=%u slot=%u mode=%u wall=%.6f bitdiff=%llu calls=%u perframe=%u\n",test,slot,mode,ms,(unsigned long long)diff,net.PairCalls(),perframe_ref);fflush(stdout);
 }}fclose(csv);
