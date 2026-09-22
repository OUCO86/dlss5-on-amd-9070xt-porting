if constexpr(sizeof...(A)==13||sizeof...(A)==14){
 const char*requested=std::getenv("DLSS5_C32_PROBE_TARGET");
 if(!c32_probe_done&&requested&&kernel==requested){
  c32_probe_done=true;auto original=Fn(module,kernel);
  auto uarg=[&](unsigned i){U x{};std::memcpy(&x,argv[i],sizeof(x));return x;};auto parg=[&](unsigned i){void*x{};std::memcpy(&x,argv[i],sizeof(x));return x;};
  unsigned wi=0;std::vector<std::pair<void*,size_t>>outputs;
  if(kernel=="c32_fast_ffn_attention_fused_half_prefix_finish_main8"){wi=6;size_t pixels=size_t(uarg(9))*uarg(10);outputs={{parg(4),pixels*32},{parg(5),pixels*32}};}
  else if(kernel=="c32_fast_ffn_attention_fused_half_chain"){wi=4;outputs={{parg(3),size_t(uarg(4))*64*32*2}};}
  else if(kernel=="c32_post_merge_head_half"){wi=8;outputs={{parg(7),size_t(uarg(9))*uarg(10)*12}};}
  else throw std::runtime_error("unknown probe target");
  U windows=uarg(wi);if(!windows||windows>=0x10000000u||windows!=groups)throw std::runtime_error("probe window ABI");
  auto launch=[&](Handle fn,void**av){api.Check(api.hipModuleLaunchKernel(fn,groups,1,1,threads,1,1,0,stream,av,nullptr),"phase launch");};
  launch(original,argv);api.Check(api.hipStreamSynchronize(stream),"reference ready");
  std::vector<std::vector<unsigned char>>reference;size_t bytes=0;
  for(auto o:outputs){if(!o.first||!o.second)throw std::runtime_error("empty output control");reference.emplace_back(o.second);api.Check(api.hipMemcpy(reference.back().data(),o.first,o.second,2),"reference output");bytes+=o.second;}
  unsigned mode=std::stoul(std::getenv("DLSS5_C32_PAIR_MODE"));auto candidate=Fn(module,kernel+"_pair"+std::to_string(mode));
  std::vector<unsigned char>actual;FILE*csv=fopen("fused.csv","wb");if(!csv)throw std::runtime_error("csv");
  fprintf(csv,"mode,slot,candidate,launches,mean_us,byte_diff,checked_bytes,start_ms,end_ms\n");
  for(unsigned slot=0;slot<8;slot++){
   bool test=slot%4==1||slot%4==2;auto fn=test?candidate:original;
   for(unsigned i=0;i<32;i++)launch(fn,argv);api.Check(api.hipStreamSynchronize(stream),"initial warm");
   auto p=std::chrono::steady_clock::now();for(unsigned i=0;i<8;i++)launch(fn,argv);api.Check(api.hipStreamSynchronize(stream),"pilot");
   double single=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-p).count()/8;
   unsigned measured=std::clamp(unsigned(std::ceil(200./single)),32u,2000u),warm=std::clamp(unsigned(std::ceil(50./single)),8u,500u);
   for(unsigned i=0;i<warm;i++)launch(fn,argv);api.Check(api.hipStreamSynchronize(stream),"warm");
   auto tick=GetTickCount64();auto start=std::chrono::steady_clock::now();
   for(unsigned i=0;i<measured;i++)launch(fn,argv);api.Check(api.hipStreamSynchronize(stream),"timed ready");
   double us=std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-start).count()/measured;auto end=GetTickCount64();
   size_t diff=0;for(size_t j=0;j<outputs.size();j++){actual.resize(outputs[j].second);api.Check(api.hipMemcpy(actual.data(),outputs[j].first,actual.size(),2),"check output");for(size_t k=0;k<actual.size();k++)diff+=actual[k]!=reference[j][k];}
   fprintf(csv,"%u,%u,%u,%u,%.9f,%llu,%llu,%llu,%llu\n",mode,slot,unsigned(test),measured,us,(unsigned long long)diff,(unsigned long long)bytes,(unsigned long long)tick,(unsigned long long)end);fflush(csv);
   if(diff)throw std::runtime_error("fused output changed");
  }
  fclose(csv);launch(original,argv);api.Check(api.hipStreamSynchronize(stream),"restore original");
 }
}
