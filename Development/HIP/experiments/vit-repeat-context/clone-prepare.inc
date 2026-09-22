  void*amp_original_weight=nullptr;std::memcpy(&amp_original_weight,argv[1],sizeof(void*));
  auto&copies=amp_weight_clones[amp_original_weight];
  if(copies.empty()){
   U inputs=0,outputs=0;std::memcpy(&inputs,argv[4],4);std::memcpy(&outputs,argv[5],4);if(inputs!=1024||outputs!=4096)throw std::runtime_error("clone weight shape");
   for(unsigned j=0;j<3;j++){void*p=nullptr;api.Check(api.hipMalloc(&p,size_t(inputs)*outputs),"weight clone allocate");api.Check(api.hipMemcpyAsync(p,amp_original_weight,size_t(inputs)*outputs,3,stream),"weight clone copy");copies.push_back(p);}
   api.Check(api.hipStreamSynchronize(stream),"weight clones ready");
  }
