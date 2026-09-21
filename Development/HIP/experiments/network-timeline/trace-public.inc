 void ProbePrepare(unsigned frames,unsigned max_launches){
  if(!probe_records.empty())throw std::runtime_error("probe already prepared");
  probe_records.resize(size_t(frames)*max_launches);probe_frames.resize(frames);
  for(auto&r:probe_records){api.Check(api.hipEventCreate(&r.begin),"probe event");api.Check(api.hipEventCreate(&r.end),"probe event");r.module.reserve(40);r.kernel.reserve(128);r.stage.reserve(48);r.args.reserve(160);}
  for(auto&f:probe_frames){api.Check(api.hipEventCreate(&f.begin),"frame event");api.Check(api.hipEventCreate(&f.end),"frame event");}
 }
 void ProbeBegin(unsigned frame){if(probe_active||frame>=probe_frames.size())throw std::runtime_error("probe frame");probe_frame=frame;probe_mark=probe_cursor;probe_frames[frame].first=probe_cursor;probe_active=true;api.Check(api.hipEventRecord(probe_frames[frame].begin,stream),"frame begin");}
 void ProbeEnd(){if(!probe_active)throw std::runtime_error("probe inactive");for(size_t i=probe_mark;i<probe_cursor;i++)probe_records[i].stage="tail";probe_frames[probe_frame].last=probe_cursor;api.Check(api.hipEventRecord(probe_frames[probe_frame].end,stream),"frame end");probe_active=false;}
 void ProbeExport(const char*path){
  Synchronize();FILE*f=fopen(path,"wb");if(!f)throw std::runtime_error("probe csv");
  fprintf(f,"frame,index,module,kernel,stage,groups,threads,count,start_ms,end_ms,duration_ms,frame_ms,scalar_args\n");
  for(unsigned frame=0;frame<probe_frames.size();frame++){auto&pf=probe_frames[frame];float frame_ms=0;api.Check(api.hipEventElapsedTime(&frame_ms,pf.begin,pf.end),"frame elapsed");
   for(size_t i=pf.first;i<pf.last;i++){auto&r=probe_records[i];float start=0,end=0,ms=0;api.Check(api.hipEventElapsedTime(&start,pf.begin,r.begin),"start elapsed");api.Check(api.hipEventElapsedTime(&end,pf.begin,r.end),"end elapsed");api.Check(api.hipEventElapsedTime(&ms,r.begin,r.end),"kernel elapsed");
    fprintf(f,"%u,%llu,%s,%s,%s,%u,%u,%u,%.9f,%.9f,%.9f,%.9f,%s\n",frame,(unsigned long long)(i-pf.first),r.module.c_str(),r.kernel.c_str(),r.stage.c_str(),r.groups,r.threads,r.count,double(start),double(end),double(ms),double(frame_ms),r.args.c_str());
   }
  }
  fclose(f);
 }
 void ProbeRelease(){Synchronize();for(auto&r:probe_records){api.hipEventDestroy(r.begin);api.hipEventDestroy(r.end);}for(auto&f:probe_frames){api.hipEventDestroy(f.begin);api.hipEventDestroy(f.end);}probe_records.clear();probe_frames.clear();probe_cursor=probe_mark=0;}
