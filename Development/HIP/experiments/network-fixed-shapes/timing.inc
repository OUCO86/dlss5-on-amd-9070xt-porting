 unsigned selected_variant=std::getenv("NFS_VARIANT")?unsigned(std::stoul(std::getenv("NFS_VARIANT"))):0;
 unsigned baseline_mode=std::getenv("NFS_BASELINE")?unsigned(std::stoul(std::getenv("NFS_BASELINE"))):0;
 unsigned frames=std::getenv("NFS_FRAMES")?unsigned(std::stoul(std::getenv("NFS_FRAMES"))):100;
 FILE*csv=fopen("network.csv","wb");if(!csv)throw std::runtime_error("csv");fprintf(csv,"variant,slot,mode,frames,mean_ms,bitdiff,replacements,start_ms,end_ms\n");
 for(unsigned variant:{1u,2u,3u,4u,7u,8u,16u,32u,64u,128u}){if(selected_variant?variant!=selected_variant:(variant==3||variant==7))continue;for(unsigned slot=0;slot<4;slot++){
  unsigned mode=(slot%4==1||slot%4==2)?variant:baseline_mode;net.SetSchedule(mode);
  for(unsigned i=0;i<40;i++){net.Enqueue(x,nullptr,y,0);net.Synchronize();}
  net.SetSchedule(mode);auto tick=GetTickCount64();auto start=std::chrono::steady_clock::now();
  for(unsigned i=0;i<frames;i++){net.Enqueue(x,nullptr,y,0);net.Synchronize();}
  double ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count()/frames;auto end=GetTickCount64();
  std::vector<float>actual(expected.size());api.Check(api.hipMemcpy(actual.data(),y,actual.size()*4,2),"raw check");size_t diff=0;for(size_t i=0;i<actual.size();i++)diff+=memcmp(&actual[i],&expected[i],4)!=0;
  unsigned replaced=net.ScheduleReplaced();if(diff||(mode&&replaced!=frames*((mode&1?8:0)+(mode&2?8:0)+(mode&4?5:0)+(mode&8?2:0)+(mode&16?13:0)+(mode&32?14:0)+(mode&64?8:0)+(mode&128?8:0)))||(!mode&&replaced))throw std::runtime_error("network output/replacement count");
  fprintf(csv,"%u,%u,%u,%u,%.9f,%llu,%u,%llu,%llu\n",variant,slot,mode,frames,ms,(unsigned long long)diff,replaced,(unsigned long long)tick,(unsigned long long)end);fflush(csv);printf("NETWORK mode=%u slot=%u ms=%.6f bitdiff=%llu replaced=%u\n",mode,slot,ms,(unsigned long long)diff,replaced);fflush(stdout);
 }
 }
 fclose(csv);
