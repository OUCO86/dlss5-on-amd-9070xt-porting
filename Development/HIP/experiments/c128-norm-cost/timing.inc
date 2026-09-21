if constexpr(sizeof...(A)==11){
if(!norm_cost_done&&kernel=="mh_ffn_fused_c128_project_mapped_g128_qkv_bytein_fb"){
 norm_cost_done=true;
 // Host ABI is the original11 arguments; feature and norm outputs are byte streams.
 void*feature{},*normalized{};std::memcpy(&feature,argv[3],sizeof(feature));std::memcpy(&normalized,argv[4],sizeof(normalized));
 U passed_rows{};std::memcpy(&passed_rows,argv[5],sizeof(passed_rows));const unsigned rows=count/128;
 if(!rows||passed_rows!=rows||groups!=rows/16)throw std::runtime_error("norm probe shape mismatch");const size_t feature_bytes=size_t(rows)*128,norm_bytes=feature_bytes*3;
 auto original=Fn(module,kernel),diagnostic=Fn(module,"c128_norm_cost");
 auto launch=[&](Handle fn,void**av){api.Check(api.hipModuleLaunchKernel(fn,groups,1,1,threads,1,1,0,stream,av,nullptr),"norm cost launch");};
 launch(original,argv);api.Check(api.hipStreamSynchronize(stream),"reference");
 std::vector<unsigned char>feature_ref(feature_bytes),norm_ref(norm_bytes),actual(std::max(feature_bytes,norm_bytes));
 api.Check(api.hipMemcpy(feature_ref.data(),feature,feature_bytes,2),"feature reference");api.Check(api.hipMemcpy(norm_ref.data(),normalized,norm_bytes,2),"norm reference");
 // All repeat modes run the SAME compiled kernel; original brackets quantify instrumentation drift.
 struct Test{unsigned mode,repeats;bool original;};
 std::vector<Test>tests={{0,1,true},{0,1,false},{0,1,false},{0,1,true}};
 for(unsigned mode=0;mode<3;mode++)for(unsigned rep:{2u,4u}){
  tests.push_back({mode,1,false});tests.push_back({mode,rep,false});tests.push_back({mode,rep,false});tests.push_back({mode,1,false});
 }

 unsigned slot=0;
 for(auto test:tests){unsigned mode=test.mode,repetitions=test.repeats;void*av[13];for(unsigned i=0;i<11;i++)av[i]=argv[i];av[11]=&mode;av[12]=&repetitions;
  auto fn=test.original?original:diagnostic;auto args_here=test.original?argv:av;
  api.Check(api.hipStreamSynchronize(stream),"drain");
  for(unsigned i=0;i<1000;i++)launch(fn,args_here);api.Check(api.hipStreamSynchronize(stream),"warmup");
  auto begin=std::chrono::steady_clock::now();for(unsigned i=0;i<6000;i++)launch(fn,args_here);api.Check(api.hipStreamSynchronize(stream),"complete");
  double us=std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-begin).count()/6000;
  size_t diff=0;api.Check(api.hipMemcpy(actual.data(),feature,feature_bytes,2),"feature check");for(size_t i=0;i<feature_bytes;i++)diff+=actual[i]!=feature_ref[i];
  api.Check(api.hipMemcpy(actual.data(),normalized,norm_bytes,2),"norm check");for(size_t i=0;i<norm_bytes;i++)diff+=actual[i]!=norm_ref[i];
  printf("NORM_COST slot=%u original=%u mode=%u repeats=%u us=%.6f byte_diff=%zu rows=%u\n",slot++,unsigned(test.original),mode,repetitions,us,diff,rows);fflush(stdout);
  if(diff)throw std::runtime_error("norm repetition changed output");
 }
 launch(original,argv);api.Check(api.hipStreamSynchronize(stream),"restore");
}
}
