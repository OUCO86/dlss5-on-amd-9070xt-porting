if constexpr(sizeof...(A)==6||sizeof...(A)==7){
 const char*requested=std::getenv("DLSS5_C32_PROBE_TARGET");
 if(!c32_probe_done&&requested&&kernel==requested){
  c32_probe_done=true;bool expand=kernel=="vit_expand_blocked_fp8_frag_bytein";auto original=Fn(module,kernel);
  auto uarg=[&](unsigned i){U v;std::memcpy(&v,argv[i],sizeof(v));return v;};auto parg=[&](unsigned i){void*v;std::memcpy(&v,argv[i],sizeof(v));return v;};
  unsigned oi=expand?2:3,ti=expand?3:4;U tokens=uarg(ti),count=tokens*(expand?4096:1024);size_t bytes=size_t(count)*(expand?1:4);void*out=parg(oi);
  if((tokens!=400&&tokens!=640)||threads!=32||groups!=(expand?tokens*4:tokens))throw std::runtime_error("schedule shape");
  unsigned launch_groups=groups,launch_threads=threads;auto launch=[&](Handle f){api.Check(api.hipModuleLaunchKernel(f,launch_groups,1,1,launch_threads,1,1,0,stream,argv,nullptr),"schedule launch");};
  launch(original);api.Check(api.hipStreamSynchronize(stream),"reference ready");std::vector<unsigned char>ref(bytes),check(bytes);api.Check(api.hipMemcpy(ref.data(),out,bytes,2),"reference");
  FILE*csv=fopen("schedule.csv","wb");if(!csv)throw std::runtime_error("csv");fprintf(csv,"variant,slot,tokens,launches,mean_us,output_diff,checked_bytes,start_ms,end_ms\n");
  for(const char*variant:{"u1","u2","u4","u8","u16","group4","group8","nmajor","token_fixed","m2"}){

   const char*filter=std::getenv("GAP_FILTER");if(filter&&std::string(variant)!=filter)continue;
   auto probe=Fn(module,std::string("probe_")+variant);std::vector<unsigned char>poison=ref;for(auto&v:poison)v^=255;
   for(unsigned slot=0;slot<8;slot++){
    bool base=slot%4==0||slot%4==3;auto fn=base?original:probe;
    unsigned warps=!base&&std::string(variant)=="group4"?4:!base&&std::string(variant)=="group8"?8:1;
    launch_threads=32*warps;launch_groups=(groups+warps-1)/warps;
    if(!base&&std::string(variant)=="m2")launch_groups=((tokens+31)/32)*64;
    api.Check(api.hipMemcpy(out,poison.data(),bytes,1),"poison output");
    for(unsigned i=0;i<32;i++)launch(fn);api.Check(api.hipStreamSynchronize(stream),"warm pilot");auto start=std::chrono::steady_clock::now();for(unsigned i=0;i<16;i++)launch(fn);api.Check(api.hipStreamSynchronize(stream),"pilot");double us=std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-start).count()/16;
    unsigned n=std::clamp(unsigned(200000./us),32u,12000u),warm=std::clamp(unsigned(50000./us),32u,4000u);
    for(unsigned i=0;i<warm;i++)launch(fn);api.Check(api.hipStreamSynchronize(stream),"warm");auto tick_start=GetTickCount64();start=std::chrono::steady_clock::now();for(unsigned i=0;i<n;i++)launch(fn);api.Check(api.hipStreamSynchronize(stream),"timed");us=std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-start).count()/n;
    auto tick_end=GetTickCount64();size_t od=0;api.Check(api.hipMemcpy(check.data(),out,bytes,2),"output check");for(size_t i=0;i<bytes;i++)od+=ref[i]!=check[i];fprintf(csv,"%s,%u,%u,%u,%.9f,%llu,%llu,%llu,%llu\n",variant,slot,tokens,n,us,(unsigned long long)od,(unsigned long long)bytes,(unsigned long long)tick_start,(unsigned long long)tick_end);fflush(csv);if(od)throw std::runtime_error("schedule output mismatch");
   }
   printf("SCHEDULE_DONE %s %s\n",kernel.c_str(),variant);fflush(stdout);
  }
  fclose(csv);launch(original);api.Check(api.hipStreamSynchronize(stream),"restore");
 }
}
