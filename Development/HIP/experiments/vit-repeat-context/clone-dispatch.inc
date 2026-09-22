 bool amp_target=kernel=="vit_expand_blocked_fp8_frag_bytein";
 if(amp_mode&&kernel=="vit_pack_input"){kernel="vit_pack_input_tiled";++amp_replaced;}
 if constexpr(sizeof...(A)==3){
  if(kernel=="vit_pack_input"||kernel=="vit_pack_input_tiled"){
   std::memcpy(&amp_pack_in,argv[0],sizeof(void*));std::memcpy(&amp_pack_out,argv[1],sizeof(void*));std::memcpy(&amp_pack_count,argv[2],sizeof(U));
   amp_pack_fn=Fn(module,kernel);amp_pack_groups=groups?groups:(count+255ull)/256;amp_pack_threads=threads;
  }
 }
 if(amp_target){
  ++amp_pairs;if(repeats_here!=1||!amp_pack_fn)throw std::runtime_error("unexpected repeat context");
  void*input=nullptr;U tokens;std::memcpy(&input,argv[0],sizeof(input));std::memcpy(&tokens,argv[3],sizeof(tokens));if(input!=amp_pack_out||amp_pack_count!=tokens*1024)throw std::runtime_error("pack/expand mismatch");
  if(amp_mode){kernel="probe_m32n64_tile_u2";groups=((tokens+31)/32)*64;++amp_replaced;}
  void*amp_original_weight=nullptr;std::memcpy(&amp_original_weight,argv[1],sizeof(void*));
  auto&copies=amp_weight_clones[amp_original_weight];
  if(copies.empty()){
   U inputs=0,outputs=0;std::memcpy(&inputs,argv[4],4);std::memcpy(&outputs,argv[5],4);if(inputs!=1024||outputs!=4096)throw std::runtime_error("clone weight shape");
   for(unsigned j=0;j<3;j++){void*p=nullptr;api.Check(api.hipMalloc(&p,size_t(inputs)*outputs),"weight clone allocate");api.Check(api.hipMemcpyAsync(p,amp_original_weight,size_t(inputs)*outputs,3,stream),"weight clone copy");copies.push_back(p);}
   api.Check(api.hipStreamSynchronize(stream),"weight clones ready");
  }

  repeats_here=amp_repeats;
 }
 for(unsigned repeat=0;repeat<repeats_here;repeat++){
  if(amp_target&&repeat){void*pa[]={&amp_pack_in,&amp_pack_out,&amp_pack_count,&reuse_gate_arg};api.Check(api.hipModuleLaunchKernel(amp_pack_fn,amp_pack_groups,1,1,amp_pack_threads,1,1,0,stream,pa,nullptr),"repeat pack");++amp_extra_pairs;}
  void*saved_weight_arg=nullptr;void*selected_weight=nullptr;
  if(amp_target&&repeat){void*original_weight=nullptr;std::memcpy(&original_weight,argv[1],sizeof(void*));void*clone=amp_weight_clones.at(original_weight).at(repeat-1);selected_weight=amp_distinct?clone:original_weight;saved_weight_arg=argv[1];argv[1]=&selected_weight;}
  api.Check(api.hipModuleLaunchKernel(Fn(module,kernel),groups?groups:(count+255ull)/256,1,1,threads,1,1,0,stream,argv,nullptr),name);
  if(saved_weight_arg)argv[1]=saved_weight_arg;
  if(amp_target)++amp_expand_launches;
 }
