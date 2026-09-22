 const unsigned frames=160;net.PrepareContext(frames);
 FILE*csv=fopen("context.csv","wb"),*detail=fopen("events.csv","wb");if(!csv||!detail)throw std::runtime_error("csv");
 fprintf(csv,"test,slot,mode,marked,frames,wall_ms,segment_ms,bitdiff,replacements,start_ms,end_ms\n");
 fprintf(detail,"test,slot,mode,frame,segment_ms\n");
 for(const char*test:{"plain_ab","marked_ab","marker_base","marker_candidate"})for(unsigned slot=0;slot<8;slot++){
  const char*only=std::getenv("CONTEXT_ONLY");if(only&&std::string(test)!=only)continue;
  bool b=slot%4==1||slot%4==2;std::string name=test;
  unsigned mode=name=="marker_base"?0:name=="marker_candidate"?1:unsigned(b);
  bool marked=name=="marked_ab"||(name.rfind("marker_",0)==0&&b);
  net.SetSchedule(mode);net.ContextFrame(-1);
  for(unsigned i=0;i<30;i++){net.ContextFrame(-1);net.Enqueue(x,nullptr,y,0);net.Synchronize();}
  net.SetSchedule(mode);auto tick=GetTickCount64();auto start=std::chrono::steady_clock::now();
  std::vector<float> immediate;
  for(unsigned i=0;i<frames;i++){net.ContextFrame(marked?int(i):-1);net.Enqueue(x,nullptr,y,0);net.Synchronize();if(marked)immediate.push_back(net.ReadContextFrame(i));}
  double wall=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count()/frames;auto end=GetTickCount64();
  unsigned invalid=0;double segment=0;if(marked){auto times=immediate;for(unsigned i=0;i<times.size();i++){if(!std::isfinite(times[i])||times[i]<=0)invalid++;segment+=times[i];fprintf(detail,"%s,%u,%u,%u,%.9f\n",test,slot,mode,i,times[i]);}segment/=times.size();fflush(detail);if(invalid){fprintf(stderr,"INVALID_EVENTS test=%s slot=%u count=%u mean=%g\n",test,slot,invalid,segment);throw std::runtime_error("invalid context elapsed (raw events saved)");}}
  std::vector<float>actual(expected.size());api.Check(api.hipMemcpy(actual.data(),y,actual.size()*4,2),"raw check");size_t diff=0;for(size_t i=0;i<actual.size();i++)diff+=memcmp(&actual[i],&expected[i],4)!=0;
  unsigned replaced=net.ScheduleReplaced();if(diff||replaced!=(mode?frames*16:0))throw std::runtime_error("network output/replacement count");
  fprintf(csv,"%s,%u,%u,%u,%u,%.9f,%.9f,%llu,%u,%llu,%llu\n",test,slot,mode,unsigned(marked),frames,wall,segment,(unsigned long long)diff,replaced,(unsigned long long)tick,(unsigned long long)end);fflush(csv);fflush(detail);
  printf("CONTEXT %s slot=%u mode=%u marked=%u wall=%.6f segment=%.6f bitdiff=%llu\n",test,slot,mode,unsigned(marked),wall,segment,(unsigned long long)diff);fflush(stdout);
 }
 net.ContextFrame(-1);net.ReleaseContext();fclose(csv);fclose(detail);
