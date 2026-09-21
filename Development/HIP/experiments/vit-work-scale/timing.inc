if constexpr(sizeof...(A)==6){
 if(!c32_probe_done&&kernel=="vit_expand_blocked_fp8_frag_bytein"){
  c32_probe_done=true;auto original=Fn(module,kernel);
  auto uarg=[&](unsigned i){U v;std::memcpy(&v,argv[i],sizeof(v));return v;};auto parg=[&](unsigned i){void*v;std::memcpy(&v,argv[i],sizeof(v));return v;};
  U tokens=uarg(3);size_t bytes=size_t(tokens)*4096;void*out=parg(2),*scratch{};
  if((tokens!=400&&tokens!=640)||groups!=tokens*4||threads!=32)throw std::runtime_error("scale shape");
  auto launch=[&](Handle f,void**args,unsigned g){api.Check(api.hipModuleLaunchKernel(f,g,1,1,32,1,1,0,stream,args,nullptr),"scale launch");};
  launch(original,argv,groups);api.Check(api.hipStreamSynchronize(stream),"reference ready");std::vector<unsigned char>ref(bytes);api.Check(api.hipMemcpy(ref.data(),out,bytes,2),"reference");
  api.Check(api.hipMalloc(&scratch,bytes*8),"scratch");std::vector<unsigned char>poison(bytes*8),actual(bytes*8);for(size_t i=0;i<poison.size();i++)poison[i]=ref[i%bytes]^255;
  FILE*csv=fopen("scale.csv","wb");if(!csv)throw std::runtime_error("csv");fprintf(csv,"bm,order,copies,slot,original,tokens,launches,groups,mean_us,per_copy_us,output_diff,checked_bytes,start_ms,end_ms\n");
  // Each original/ref probe comparison is ABBA twice. Calibration copies=1 included.
  for(unsigned bm:{1u,2u})for(const char*order:{"major","interleave"})for(U copies:{1u,2u,4u,8u}){
   const char*filter=std::getenv("SCALE_FILTER");if(filter&&std::string(order)!=filter)continue;
   auto probe=Fn(module,std::string("probe_m")+std::to_string(bm)+"_"+order);
   for(unsigned slot=0;slot<8;slot++){
    bool base=slot%4==0||slot%4==3;U active_copies=base?1:copies;unsigned g=base?groups:((tokens+16*bm-1)/(16*bm))*64*copies;auto fn=base?original:probe;
    void*args[7];for(unsigned i=0;i<7;i++)args[i]=argv[i];args[2]=&scratch;if(!base)args[4]=&copies;
    size_t checked=bytes*active_copies;api.Check(api.hipMemcpy(scratch,poison.data(),checked,1),"poison");
    launch(fn,args,g);api.Check(api.hipStreamSynchronize(stream),"precheck ready");api.Check(api.hipMemcpy(actual.data(),scratch,checked,2),"precheck");for(size_t i=0;i<checked;i++)if(actual[i]!=ref[i%bytes])throw std::runtime_error("replicated precheck mismatch");
    for(unsigned i=0;i<32;i++)launch(fn,args,g);api.Check(api.hipStreamSynchronize(stream),"pilot ready");auto start=std::chrono::steady_clock::now();for(unsigned i=0;i<16;i++)launch(fn,args,g);api.Check(api.hipStreamSynchronize(stream),"pilot");double us=std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-start).count()/16;
    unsigned n=std::clamp(unsigned(400000./us),32u,16000u),warm=std::clamp(unsigned(100000./us),32u,4000u);
    for(unsigned i=0;i<warm;i++)launch(fn,args,g);api.Check(api.hipStreamSynchronize(stream),"warm");auto tick=GetTickCount64();start=std::chrono::steady_clock::now();for(unsigned i=0;i<n;i++)launch(fn,args,g);api.Check(api.hipStreamSynchronize(stream),"timed");us=std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-start).count()/n;auto end=GetTickCount64();
    api.Check(api.hipMemcpy(actual.data(),scratch,checked,2),"check");size_t diff=0;for(size_t i=0;i<checked;i++)diff+=actual[i]!=ref[i%bytes];
    fprintf(csv,"%u,%s,%u,%u,%u,%u,%u,%u,%.9f,%.9f,%llu,%llu,%llu,%llu\n",bm,order,copies,slot,unsigned(base),tokens,n,g,us,us/active_copies,(unsigned long long)diff,(unsigned long long)checked,(unsigned long long)tick,(unsigned long long)end);fflush(csv);if(diff)throw std::runtime_error("replicated output mismatch");
   }
   printf("SCALE_DONE bm=%u order=%s copies=%u\n",bm,order,copies);fflush(stdout);
  }
  fclose(csv);api.hipFree(scratch);launch(original,argv,groups);api.Check(api.hipStreamSynchronize(stream),"restore");
 }
}
