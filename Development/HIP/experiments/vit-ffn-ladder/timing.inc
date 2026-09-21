if constexpr(sizeof...(A)==6||sizeof...(A)==7){
 const char*requested=std::getenv("DLSS5_C32_PROBE_TARGET");
 if(!c32_probe_done&&requested&&kernel==requested){
  c32_probe_done=true;bool expand=kernel=="vit_expand_blocked_fp8_frag_bytein";
  auto original=Fn(module,kernel),rawfn=Fn(module,expand?"ladder_expand_raw":"ladder_contract_raw"),epifn=Fn(module,"ladder_epilogue");
  auto uarg=[&](unsigned i){U v;std::memcpy(&v,argv[i],sizeof(v));return v;};auto parg=[&](unsigned i){void*v;std::memcpy(&v,argv[i],sizeof(v));return v;};
  unsigned oi=expand?2:3,ti=expand?3:4;U tokens=uarg(ti),count=tokens*(expand?4096:1024);size_t bytes=size_t(count)*(expand?1:4);void*out=parg(oi),*raw{};
  if((tokens!=400&&tokens!=640)||threads!=32||groups!=(expand?tokens*4:tokens))throw std::runtime_error("ladder shape");
  api.Check(api.hipMalloc(&raw,size_t(count)*4),"raw buffer");
  void*rawargs[sizeof...(A)+1];for(unsigned i=0;i<sizeof...(A)+1;i++)rawargs[i]=argv[i];rawargs[oi]=&raw;
  auto launch=[&](Handle f,void**args,unsigned g,unsigned t){api.Check(api.hipModuleLaunchKernel(f,g,1,1,t,1,1,0,stream,args,nullptr),"ladder launch");};
  launch(original,argv,groups,threads);api.Check(api.hipStreamSynchronize(stream),"reference ready");
  std::vector<unsigned char>ref(bytes),check(bytes),rawref(size_t(count)*4),rawcheck(rawref.size());api.Check(api.hipMemcpy(ref.data(),out,bytes,2),"reference");
  FILE*csv=fopen("ladder.csv","wb");if(!csv)throw std::runtime_error("csv");fprintf(csv,"variant,slot,tokens,launches,mean_us,output_diff,raw_diff,checked_bytes\n");
  for(const char*variant:{"raw","act","split"}){
   if(!expand&&std::string(variant)=="act")continue;
   bool act=std::string(variant)=="act",split=std::string(variant)=="split";auto fn=act?Fn(module,"ladder_expand_act"):rawfn;U mode=expand?(act?1:0):2;
   void*ea[]={&raw,&out,&count,&mode};
   launch(fn,rawargs,groups,threads);api.Check(api.hipStreamSynchronize(stream),"raw reference ready");api.Check(api.hipMemcpy(rawref.data(),raw,rawref.size(),2),"raw reference");
   for(unsigned slot=0;slot<8;slot++){
    bool base=slot%4==0||slot%4==3;
    auto run=[&](){if(base)launch(original,argv,groups,threads);else{launch(fn,rawargs,groups,threads);if(split)launch(epifn,ea,(count+255)/256,256);}};
    for(unsigned i=0;i<32;i++)run();api.Check(api.hipStreamSynchronize(stream),"warm pilot");auto start=std::chrono::steady_clock::now();for(unsigned i=0;i<16;i++)run();api.Check(api.hipStreamSynchronize(stream),"pilot");double us=std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-start).count()/16;
    unsigned n=std::clamp(unsigned(200000./us),32u,12000u),warm=std::clamp(unsigned(50000./us),32u,4000u);
    for(unsigned i=0;i<warm;i++)run();api.Check(api.hipStreamSynchronize(stream),"warm");start=std::chrono::steady_clock::now();for(unsigned i=0;i<n;i++)run();api.Check(api.hipStreamSynchronize(stream),"timed");us=std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-start).count()/n;
    size_t rd=0,od=0;if(!base){api.Check(api.hipMemcpy(rawcheck.data(),raw,rawcheck.size(),2),"raw check");for(size_t i=0;i<rawref.size();i++)rd+=rawref[i]!=rawcheck[i];if(!split){launch(epifn,ea,(count+255)/256,256);api.Check(api.hipStreamSynchronize(stream),"composed ready");}}
    api.Check(api.hipMemcpy(check.data(),out,bytes,2),"output check");for(size_t i=0;i<bytes;i++)od+=ref[i]!=check[i];fprintf(csv,"%s,%u,%u,%u,%.9f,%llu,%llu,%llu\n",variant,slot,tokens,n,us,(unsigned long long)od,(unsigned long long)rd,(unsigned long long)bytes);fflush(csv);if(rd||od)throw std::runtime_error("ladder output mismatch");
   }
   printf("LADDER_DONE %s %s\n",kernel.c_str(),variant);fflush(stdout);
  }
  fclose(csv);api.hipFree(raw);launch(original,argv,groups,threads);api.Check(api.hipStreamSynchronize(stream),"restore");
 }
}
