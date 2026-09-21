if constexpr(sizeof...(A)==3){
 if(!c32_probe_done&&kernel=="vit_pack_input"){std::memcpy(&layout_float_input,argv[0],sizeof(void*));std::memcpy(&layout_count,argv[2],sizeof(U));}
}
if constexpr(sizeof...(A)==6){
 if(!c32_probe_done&&kernel=="vit_expand_blocked_fp8_frag_bytein"){
  c32_probe_done=true;auto original=Fn(module,kernel),tiled=Fn(module,"probe_vit_tiled_fixed"),dynamic=Fn(module,"vit_expand_blocked_fp8_frag_tiledin"),rowpack=Fn(module,"vit_pack_input"),tilepack=Fn(module,"vit_pack_input_tiled");
  auto uarg=[&](unsigned i){U v;std::memcpy(&v,argv[i],sizeof(v));return v;};auto parg=[&](unsigned i){void*v;std::memcpy(&v,argv[i],sizeof(v));return v;};
  U tokens=uarg(3),pack_count=tokens*1024;size_t input_bytes=pack_count,output_bytes=size_t(tokens)*4096;void*row_in=parg(0),*out=parg(2),*tile_in{},*matrix_out{},*gate=nullptr;
  if(!layout_float_input||layout_count!=pack_count||(tokens!=400&&tokens!=640)||groups!=tokens*4||threads!=32)throw std::runtime_error("layout shape");
  auto launch=[&](Handle f,void**args,unsigned g,unsigned t){api.Check(api.hipModuleLaunchKernel(f,g,1,1,t,1,1,0,stream,args,nullptr),"layout launch");};
  launch(original,argv,groups,32);api.Check(api.hipStreamSynchronize(stream),"reference ready");
  std::vector<unsigned char>ref(output_bytes),rowref(input_bytes),tileref(input_bytes),check(output_bytes),poison(output_bytes);api.Check(api.hipMemcpy(ref.data(),out,output_bytes,2),"reference");api.Check(api.hipMemcpy(rowref.data(),row_in,input_bytes,2),"input reference");
  for(U row=0;row<tokens;row++)for(U k=0;k<1024;k++){size_t off=((row/16)*32+k/32)*512+((k%32)/8)*128+(row%16)*8+k%8;tileref[off]=rowref[size_t(row)*1024+k];}
  api.Check(api.hipMalloc(&tile_in,input_bytes),"tile input");api.Check(api.hipMalloc(&matrix_out,output_bytes),"matrix output");
  void*packrow[]={&layout_float_input,&row_in,&pack_count,&gate},*packtile[]={&layout_float_input,&tile_in,&pack_count,&gate};unsigned pack_groups=(pack_count/4+255)/256;
  void*rowargs[7],*tileargs[7];for(unsigned i=0;i<7;i++)rowargs[i]=tileargs[i]=argv[i];rowargs[2]=tileargs[2]=&matrix_out;tileargs[0]=&tile_in;
  FILE*csv=fopen("layout.csv","wb");if(!csv)throw std::runtime_error("csv");fprintf(csv,"stage,slot,tiled,tokens,launches,mean_us,output_diff,checked_bytes,start_ms,end_ms\n");
  for(const char*stage:{"matrix","pack","pair","dynamic_control"})for(unsigned slot=0;slot<8;slot++){
   bool test=slot%4==1||slot%4==2,packing=std::string(stage)=="pack",pair=std::string(stage)=="pair",dyn=std::string(stage)=="dynamic_control";
   auto mat=test?(dyn?dynamic:tiled):original;auto args=test?tileargs:rowargs;auto pack=test?tilepack:rowpack;auto pa=test?packtile:packrow;
   // Each stage starts with both valid inputs; then poison the buffer this stage must write.
   launch(rowpack,packrow,pack_groups,256);launch(tilepack,packtile,pack_groups,256);api.Check(api.hipStreamSynchronize(stream),"inputs ready");
   const auto&expected=packing?(test?tileref:rowref):ref;size_t bytes=expected.size();for(size_t i=0;i<bytes;i++)poison[i]=expected[i]^255;void*dest=packing?(test?tile_in:row_in):matrix_out;api.Check(api.hipMemcpy(dest,poison.data(),bytes,1),"poison");
   auto run=[&](){if(packing||pair)launch(pack,pa,pack_groups,256);if(!packing)launch(mat,args,groups,32);};
   run();api.Check(api.hipStreamSynchronize(stream),"precheck");api.Check(api.hipMemcpy(check.data(),dest,bytes,2),"precheck copy");for(size_t i=0;i<bytes;i++)if(check[i]!=expected[i])throw std::runtime_error("layout precheck mismatch");
   for(unsigned i=0;i<32;i++)run();api.Check(api.hipStreamSynchronize(stream),"warm pilot");auto start=std::chrono::steady_clock::now();for(unsigned i=0;i<16;i++)run();api.Check(api.hipStreamSynchronize(stream),"pilot");double us=std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-start).count()/16;
   unsigned n=std::clamp(unsigned(400000./us),32u,40000u),warm=std::clamp(unsigned(100000./us),32u,10000u);for(unsigned i=0;i<warm;i++)run();api.Check(api.hipStreamSynchronize(stream),"warm");auto tick=GetTickCount64();start=std::chrono::steady_clock::now();for(unsigned i=0;i<n;i++)run();api.Check(api.hipStreamSynchronize(stream),"timed");us=std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-start).count()/n;auto end=GetTickCount64();
   api.Check(api.hipMemcpy(check.data(),dest,bytes,2),"check");size_t diff=0;for(size_t i=0;i<bytes;i++)diff+=check[i]!=expected[i];fprintf(csv,"%s,%u,%u,%u,%u,%.9f,%llu,%llu,%llu,%llu\n",stage,slot,unsigned(test),tokens,n,us,(unsigned long long)diff,(unsigned long long)bytes,(unsigned long long)tick,(unsigned long long)end);fflush(csv);if(diff)throw std::runtime_error("layout output changed");
   if(slot==7){printf("LAYOUT_DONE %s\n",stage);fflush(stdout);}
  }
  fclose(csv);launch(rowpack,packrow,pack_groups,256);launch(original,argv,groups,32);api.Check(api.hipStreamSynchronize(stream),"restore");api.hipFree(tile_in);api.hipFree(matrix_out);
 }
}
