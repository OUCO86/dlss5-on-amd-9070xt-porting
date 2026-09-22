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
  repeats_here=amp_repeats;
 }
 for(unsigned repeat=0;repeat<repeats_here;repeat++){
  if(amp_target&&repeat){void*pa[]={&amp_pack_in,&amp_pack_out,&amp_pack_count,&reuse_gate_arg};api.Check(api.hipModuleLaunchKernel(amp_pack_fn,amp_pack_groups,1,1,amp_pack_threads,1,1,0,stream,pa,nullptr),"repeat pack");++amp_extra_pairs;}
  api.Check(api.hipModuleLaunchKernel(Fn(module,kernel),groups?groups:(count+255ull)/256,1,1,threads,1,1,0,stream,argv,nullptr),name);
  if(amp_target)++amp_expand_launches;
 }
