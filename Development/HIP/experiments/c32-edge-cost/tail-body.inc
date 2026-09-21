template<bool HalfOutput,bool Mapped=false,bool RawMapped=false,bool Merge=false,bool RgbHead=false,bool Finish=false,bool Main8=false,bool DownCrop=false,bool Prefix=false>
DEV void c32_probe_tail_body(const float*raw_input,const float*fw,const float*w,float*out,uint windows,uint residual_mode,uint raw_output,uint sourcew=0,uint sourceh=0,uint sx=0,uint sy=0,uint prevw=0,uint prevsx=0,uint prevsy=0,const float*skip=nullptr,const float*scales=nullptr,const float*color=nullptr,const float*headw=nullptr,float*rgb=nullptr,float rgb_scale=0.f,float*main=nullptr,float*down=nullptr,const float*rgba=nullptr,const float*hist=nullptr,uint seed=0,uint temporal=0){
 uint probe_repeats=windows>>28;windows&=0x0fffffffu;if(!probe_repeats)probe_repeats=1;
 uint window=bid();if(window>=windows)return;uint tid=__builtin_amdgcn_workitem_id_x(),wave=tid/32,first=wave*16,base=window*64;
 union Scratch {float raw[64*33];_Float16 ex[64*66];unsigned char hidden[64*132];};
 __attribute__((shared)) Scratch scratch;
 __attribute__((shared)) unsigned char packed[3*64*36];
#if HIP_C32_VT
 __attribute__((shared)) unsigned char vt[32*68]; // V transposed [col][key]: the AV B fragment is 8 contiguous bytes (the [key][col] rows needed 8 byte gathers per fragment)
#endif
#if HIP_C32_REGISTER_FFN
 h8 saved_ffn[2];
#if HIP_C32_ALIAS_FFN_V
 // Q/K writes are disjoint; V overwrites only after this wave finishes its FFN reads.
 // The final residual remains in saved_ffn registers.
 unsigned char*ffn8=packed+128*36;
#else
 __attribute__((shared)) unsigned char ffn8[64*36];
#endif
#else
 __attribute__((shared)) _Float16 ffn[64*34];
#endif
 if(residual_mode!=0&&residual_mode!=3)return;
 // Stage input64x36 only; FFN matrices are loaded directly from global weights.
#if HIP_C32_LANE_STAGE
 // Lane staging (HLSL ffn_fused shape): each wave stages its own 16 tokens; lanes 0..15 compute the mapped source
 // index of one token once, then for every token the 32 lanes load channel l of that token (one contiguous 128-byte
 // row) with the index broadcast by readlane. Same values as mapped_c32_input, 64 index computations per window
 // instead of 2048. The f16 copy (exact: every mapped source is H()-rounded) feeds the mode-0 residual.
 constexpr bool NeedIn16=Mapped&&!RawMapped;
 __attribute__((shared)) _Float16 in16[NeedIn16?64*34:1];
 f8 pre_acc[2];pre_acc[0]=f8{};pre_acc[1]=f8{};
 if constexpr(Prefix){uint l=tid%32;float*values=scratch.raw+wave*256;_Float16*pre16=reinterpret_cast<_Float16*>(scratch.raw+1024)+wave*512; // scratch is free until the FFN hidden writes
  if(l<16){float f[16]{};fused_prefix_values(rgba,hist,base+first+l,sourcew,seed,temporal,f);for(uint k=0;k<16;k++)values[l*16+k]=f[k];}
  sync_window();
  for(uint tile=0;tile<2;tile++){h8 a{};for(uint e=0;e<8;e++){uint k=tile*16+gr()*8+e;a[e]=(_Float16)(k<16?values[rc()*16+k]:0.f);}
   for(uint col=0;col<2;col++){h8 b{};for(uint e=0;e<8;e++){uint k=tile*16+gr()*8+e;b[e]=(_Float16)(k<16?fw[(col*16+rc())*16+k]:0.f);}pre_acc[col]=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(a,b,pre_acc[col]);}}
  for(uint col=0;col<2;col++)for(uint e=0;e<8;e++){float v=Hrtz(pre_acc[col][e]);pre_acc[col][e]=v;pre16[(gr()*8+e)*32+col*16+rc()]=(_Float16)v;}
  sync_window();
  #pragma unroll
  for(uint j=0;j<16;j++)packed[(first+j)*36+l]=static_cast<unsigned char>(fp8(float(pre16[j*32+l])));
 }else
 {uint l=tid%32;int mine=-1,mine2=-1;
  if constexpr(Mapped){if(l<16){uint token=first+l,ww=sourcew+2*sx;int x=int((window%(ww/8))*8+token%8)-int(sx),y=int((window/(ww/8))*8+token/8)-int(sy);
   if(x>=0&&y>=0&&x<int(sourcew)&&y<int(sourceh)){if constexpr(Merge){mine=int((uint(y)*sourcew+uint(x))*32);mine2=int(((uint(y)/2)*(sourcew/2)+uint(x)/2)*32);}else if constexpr(RawMapped){uint px=uint(x)+prevsx,py=uint(y)+prevsy,tile=(py/8)*(prevw/8)+px/8,token0=(py%8)*8+px%8;mine=int((tile*64+token0)*32);}else mine=int((uint(y)*sourcew+uint(x))*32);}}}
#if HIP_C32_STAGE_PREFETCH
  // Pass 1: every token's load is issued with a branch-free index (out-of-window tokens read element l of the buffer and
  // are zeroed below), so the 16 loads overlap; pass 2 converts. Values identical to the single-pass form.
  float lv[16];uint hb[16];int srcs[16];
  #pragma unroll
  for(uint j=0;j<16;j++){uint row=first+j;
   if constexpr(!Mapped){lv[j]=raw_input[(base+row)*32+l];srcs[j]=0;hb[j]=0;}
   else{int src=__builtin_amdgcn_readlane(mine,j);srcs[j]=src;uint idx=src>=0?uint(src):0u;hb[j]=0;
    if constexpr(Merge){int src2=__builtin_amdgcn_readlane(mine2,j);uint idx2=src2>=0?uint(src2):0u;hb[j]=reinterpret_cast<const unsigned char*>(skip)[idx+l];lv[j]=raw_input[idx2+l];}
    else if constexpr(RawMapped)lv[j]=float(reinterpret_cast<const _Float16*>(raw_input)[idx+l]);
    else lv[j]=raw_input[idx+l];}}
  #pragma unroll
  for(uint j=0;j<16;j++){uint row=first+j;float v;
   if constexpr(!Mapped)v=lv[j];
   else{float c;if constexpr(Merge){float high=__builtin_amdgcn_cvt_f32_fp8(int(hb[j]),0);c=Hrtz(Hrtz(lv[j]*scales[l])+high*scales[32+l]);}else if constexpr(RawMapped)c=F(lv[j]);else c=lv[j];v=srcs[j]>=0?c:0.f;}
   packed[row*36+l]=static_cast<unsigned char>(fp8(v));
   if constexpr(NeedIn16)in16[row*34+l]=(_Float16)v;
  }}
#else
  #pragma unroll
  for(uint j=0;j<16;j++){uint row=first+j;float v=0.f;
   if constexpr(!Mapped)v=raw_input[(base+row)*32+l];
   else{int src=__builtin_amdgcn_readlane(mine,j);if(src>=0){if constexpr(Merge){int src2=__builtin_amdgcn_readlane(mine2,j);float high=__builtin_amdgcn_cvt_f32_fp8(int(reinterpret_cast<const unsigned char*>(skip)[uint(src)+l]),0);v=Hrtz(Hrtz(raw_input[uint(src2)+l]*scales[l])+high*scales[32+l]);}else if constexpr(RawMapped)v=F(float(reinterpret_cast<const _Float16*>(raw_input)[uint(src)+l]));else v=raw_input[uint(src)+l];}}
   packed[row*36+l]=static_cast<unsigned char>(fp8(v));
   if constexpr(NeedIn16)in16[row*34+l]=(_Float16)v;
  }}
#endif
#elif HIP_C32_INPUT_DWORD
 for(uint i=tid;i<64*9;i+=128){uint row=i/9,k=(i%9)*4,word=0;if(k<32)for(uint e=0;e<4;e++)word|=(fp8(Mapped?mapped_c32_input<RawMapped,Merge>(raw_input,window,row,k+e,sourcew,sourceh,sx,sy,prevw,prevsx,prevsy,skip,scales):raw_input[(base+row)*32+k+e])&255u)<<(e*8);__builtin_memcpy(packed+i*4,&word,4);}
#else
 for(uint i=tid;i<64*36;i+=128){uint row=i/36,k=i%36;packed[i]=k<32?static_cast<unsigned char>(fp8(Mapped?mapped_c32_input<RawMapped,Merge>(raw_input,window,row,k,sourcew,sourceh,sx,sy,prevw,prevsx,prevsy,skip,scales):raw_input[(base+row)*32+k])):0;}
#endif
#if HIP_C32_LOCAL_FFN_SYNC
 sync_owned_rows();
#else
 sync_window();
#endif
#if HIP_C32_ABLATE!=1
 C32_LOOP for(uint col=0;col<128;col+=16){f8 sum{};
  for(uint kt=0;kt<2;kt++){i2 a{},b{};uint k=kt*16+gr()*8;a=load8(packed+(first+rc())*36+k);b=matrix8(fw+512,(col+rc())*32+k);sum=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,sum);}
  for(uint e=0;e<8;e++){float v=sum[e],g=clampf(v,-4.f,4.f),q=absf(g)*(-.055908203125f)+.447265625f,p=g*q+.89453125f;scratch.hidden[(first+gr()*8+e)*132+col+rc()]=static_cast<unsigned char>(fp8(v*p));}
 }
#endif

#if HIP_C32_LOCAL_FFN_SYNC
 sync_owned_rows();
#else
 sync_window();
#endif
 f8 acc[2];acc[0]=f8{};acc[1]=f8{};
 if(residual_mode==0){for(uint ci=0;ci<2;ci++)for(uint e=0;e<8;e++){uint row=first+gr()*8+e,c=ci*16+rc();float x;
#if HIP_C32_LANE_STAGE
   if constexpr(Prefix)x=pre_acc[ci][e];else if constexpr(NeedIn16)x=float(in16[row*34+c]);else x=Mapped?mapped_c32_input<RawMapped,Merge>(raw_input,window,row,c,sourcew,sourceh,sx,sy,prevw,prevsx,prevsy,skip,scales):raw_input[(base+row)*32+c];
#else
   x=Mapped?mapped_c32_input<RawMapped,Merge>(raw_input,window,row,c,sourcew,sourceh,sx,sy,prevw,prevsx,prevsy,skip,scales):raw_input[(base+row)*32+c];
#endif
   acc[ci][e]=clampf(x,-448.f,448.f)*fw[8704+c];}}
#if HIP_C32_DIAG_WEIGHTS
 else{for(uint part=0;part<3;part++)for(uint ci=0;ci<2;ci++)for(uint kt=0;kt<2;kt++){i2 a=load8(packed+(first+rc())*36+kt*16+gr()*8),b=matrix8(fw,34944+((part*2+ci)*2+kt)*512+(gr()*16+rc())*8);acc[ci]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,acc[ci]);}}
#else
 else{for(uint part=0;part<3;part++)for(uint ci=0;ci<2;ci++){uint c=ci*16+rc();float remaining=fw[8704+c],piece=0;for(uint j=0;j<=part;j++){piece=scale_piece(remaining);remaining-=piece;}
   for(uint kt=0;kt<2;kt++){i2 a{},b{};
#if HIP_C32_LOCAL_FFN_SYNC
    a=load8(packed+(first+rc())*36+kt*16+gr()*8);for(uint e=0;e<8;e++){uint k=kt*16+gr()*8+e;put_bits(b,e,k==c?fp8(piece):0u);}
#else
    for(uint e=0;e<8;e++){uint k=kt*16+gr()*8+e;put_bits(a,e,packed[(first+rc())*36+k]);put_bits(b,e,k==c?fp8(piece):0u);}
#endif
    acc[ci]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,acc[ci]);}
  }}
#endif
#if HIP_C32_ABLATE!=1
 C32_LOOP for(uint chunk=0;chunk<4;chunk++)for(uint ci=0;ci<2;ci++){
  for(uint kt=0;kt<2;kt++){i2 a{},b{};uint k=chunk*32+kt*16+gr()*8;a=load8(scratch.hidden+(first+rc())*132+k);b=matrix8(fw+4608,(ci*16+rc())*128+k);acc[ci]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,acc[ci]);}
 }
#endif

#if HIP_C32_ALIAS_FFN_V && HIP_C32_REGISTER_FFN
 // Preserve the validated contraction-to-FFN phase boundary.
 sync_window();
#endif
 for(uint ci=0;ci<2;ci++)for(uint e=0;e<8;e++){
#if HIP_C32_REGISTER_FFN
  float v=Hrtz(acc[ci][e]);saved_ffn[ci][e]=(_Float16)v;ffn8[(first+gr()*8+e)*36+ci*16+rc()]=static_cast<unsigned char>(fp8(v));
#else
  ffn[(first+gr()*8+e)*34+ci*16+rc()]=(_Float16)Hrtz(acc[ci][e]);
#endif
 }
 sync_window();
 // A single raw QKV plane is reused after its norm has been packed separately.
 C32_LOOP for(uint part=0;part<3;part++){
  for(uint col=0;col<32;col+=16){f8 acc{};
   for(uint kt=0;kt<2;kt++){i2 a{},b{};
#if HIP_C32_REGISTER_FFN
    a=load8(ffn8+(first+rc())*36+kt*16+gr()*8);
#endif
    for(uint e=0;e<8;e++){uint k=kt*16+gr()*8+e;
#if !HIP_C32_REGISTER_FFN
     put(a,e,float(ffn[(first+rc())*34+k]));
#endif
    }b=matrix8(w,part*1024+(col+rc())*32+kt*16+gr()*8);acc=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,acc);}
   for(uint e=0;e<8;e++)scratch.raw[(first+gr()*8+e)*33+col+rc()]=acc[e];
  }
  sync_owned_rows();f8 sum{};
  if(part<2)for(uint kt=0;kt<2;kt++){h8 a{},ones{};for(uint e=0;e<8;e++){uint k=kt*16+gr()*8+e;float v=scratch.raw[(first+rc())*33+k];a[e]=(_Float16)(v*v);ones[e]=(_Float16)1.f;}sum=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(a,ones,sum);}
  for(uint col=0;col<32;col+=16)for(uint e=0;e<8;e++){uint row=first+gr()*8+e;float v=scratch.raw[row*33+col+rc()];if(part<2)v*=__builtin_amdgcn_rsqf(maxf(sum[e],6.198883056640625e-5f))*(part==0?w[8192]:1.f);
#if HIP_C32_VT
   if(part==2)vt[(col+rc())*68+row]=static_cast<unsigned char>(fp8(v));else
#endif
   packed[(part*64+row)*36+col+rc()]=static_cast<unsigned char>(fp8(v));}
  sync_owned_rows();
 }
#if HIP_C32_LOCAL_QKV_SYNC
 sync_window(); // Attention reads K/V rows owned by all four waves.
#endif
 // Q/K packed rows: 36-byte stride. Exponent values stored exactly as half bits.
#if HIP_C32_LOCAL_ATTN_SYNC
 // Wave-private from here on: scores/ex rows, probability rows (in the wave's own ex slice) and the AV bytes (own Q rows)
 // are read only by the wave that wrote them; K/V rows were published by the group sync above.
 unsigned char*prob=reinterpret_cast<unsigned char*>(scratch.ex)+first*132;
#define ATTN_SYNC() sync_owned_rows()
#else
 unsigned char*prob=packed;
#define ATTN_SYNC() sync_window()
#endif
 // Keep the generated half exponent values for probability normalization.
 // Both fixed-index loops must unroll: dynamic vector-array indexing expands
 // into thousands of lane/select instructions on COMGR (2026-09-19).
 h8 saved_ex[4];
 f8 av[2];av[0]=f8{};av[1]=f8{};
#if HIP_C32_ABLATE!=2
 _Pragma("unroll 4") for(uint key=0;key<64;key+=16){f8 acc{};
  for(uint kt=0;kt<2;kt++){i2 a{},b{};uint k=kt*16+gr()*8;a=load8(packed+(first+rc())*36+k);b=load8(packed+(64+key+rc())*36+k);acc=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,acc);}
  _Pragma("unroll 8") for(uint e=0;e<8;e++){uint q=first+gr()*8+e,k=key+rc();float score=acc[e]+w[4096+q*64+k],affine=clampf(score*.044921875f+1.30078125f,1.03125f,1.5693359375f);uint ah=(bits(affine)>>13)-0x1c000u;ushort hb=static_cast<ushort>(((ah<<5)+0x8000u)&65535u);scratch.ex[q*66+k]=__builtin_bit_cast(_Float16,hb);saved_ex[key/16][e]=__builtin_bit_cast(_Float16,hb);}
 }
 ATTN_SYNC();
 // Scores no longer consume Q/K; their 4608 bytes become 64 probability rows of 68 bytes.
 {f8 sum{};for(uint kt=0;kt<4;kt++){h8 a{},ones{};for(uint e=0;e<8;e++){uint k=kt*16+gr()*8+e;a[e]=scratch.ex[(first+rc())*66+k];ones[e]=(_Float16)1.f;}sum=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(a,ones,sum);}
#if HIP_C32_LOCAL_ATTN_SYNC
  float pv[4][8];for(uint key=0;key<64;key+=16)for(uint e=0;e<8;e++){uint row=first+gr()*8+e,k=key+rc();pv[key/16][e]=float(scratch.ex[row*66+k])*norm_inverse(sum[e]);}
  ATTN_SYNC(); // every lane of this wave has read its ex values before the rows are reused for probabilities
  for(uint key=0;key<64;key+=16)for(uint e=0;e<8;e++){uint row=gr()*8+e,k=key+rc();prob[row*68+k]=static_cast<unsigned char>(fp8(pv[key/16][e]));}
#else
  _Pragma("unroll 4") for(uint key=0;key<64;key+=16) _Pragma("unroll 8") for(uint e=0;e<8;e++){uint row=first+gr()*8+e,k=key+rc();float v=float(saved_ex[key/16][e])*norm_inverse(sum[e]);prob[row*68+k]=static_cast<unsigned char>(fp8(v));}
#endif
 }
 ATTN_SYNC();
 // Both AV column fragments stay live until every wave has finished reading probability rows.
 for(uint ci=0;ci<2;ci++){f8 acc{};uint col=ci*16;
  for(uint kt=0;kt<4;kt++){i2 a{},b{};
#if HIP_C32_VT
   __builtin_memcpy(&a,prob+(first+rc())*68+kt*16+gr()*8,8);__builtin_memcpy(&b,vt+(col+rc())*68+kt*16+gr()*8,8);
#else
   for(uint e=0;e<8;e++){uint k=kt*16+gr()*8+e;
#if HIP_C32_LOCAL_ATTN_SYNC
   put_bits(a,e,prob[rc()*68+k]);
#else
   put_bits(a,e,prob[(first+rc())*68+k]);
#endif
   put_bits(b,e,packed[(128+k)*36+col+rc()]);}
#endif
   acc=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,acc);}av[ci]=acc;
 }
#endif

 ATTN_SYNC();
 for(uint ci=0;ci<2;ci++)for(uint e=0;e<8;e++)packed[(first+gr()*8+e)*36+ci*16+rc()]=static_cast<unsigned char>(fp8(av[ci][e]));
 ATTN_SYNC();
#if HIP_C32_HOIST_PW
 // The projection scale is per column: read the lane's two values once. Inside the loop the reads sat between the out[]
 // stores, so the compiler re-issued global_load + s_wait_loadcnt 0 for every one of the 16 outputs (ISA, 2026-09-17).
 const float pw0=w[8193+rc()],pw1=w[8193+16+rc()];
#endif
#if HIP_C32_ABLATE!=3
 C32_LOOP for(uint col=0;col<32;col+=16){f8 acc{};
  for(uint kt=0;kt<2;kt++){i2 a{},b{};for(uint e=0;e<8;e++){uint k=kt*16+gr()*8+e;put_bits(a,e,packed[(first+rc())*36+k]);}b=matrix8(w,3072+(col+rc())*32+kt*16+gr()*8);acc=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,acc);}
  for(uint e=0;e<8;e++){uint i=(base+first+gr()*8+e)*32+col+rc();float residual;
#if HIP_C32_REGISTER_FFN
   residual=float(saved_ffn[col/16][e]);
#else
   residual=float(ffn[(first+gr()*8+e)*34+col+rc()]);
#endif
#if HIP_C32_HOIST_PW
   float prod=residual*(col==0?pw0:pw1),v=Hrtz(acc[e]+prod);
#else
   float prod=residual*w[8193+col+rc()],v=Hrtz(acc[e]+prod);
#endif
   if constexpr(RgbHead||Finish)scratch.ex[(first+gr()*8+e)*34+col+rc()]=(_Float16)v; // raw_output is 1 here: v is the half the finish/head would have read back
   if constexpr(Finish){if(out)reinterpret_cast<_Float16*>(out)[i]=(_Float16)v;}
   else if constexpr(RgbHead){}
   else if constexpr(HalfOutput)reinterpret_cast<_Float16*>(out)[i]=(_Float16)(raw_output?v:F(v));else out[i]=raw_output?v:F(v);}
 }
#endif

 _Pragma("clang loop unroll(disable)") for(uint rep=0;rep<probe_repeats;rep++){asm volatile("" ::: "memory");
 if constexpr(Finish){
  // c32_finish_crop_half / c32_finish_fast_half_main8 in the epilogue (HLSL DLSS5_C32_EPILOGUE finish shape): the wave's 16
  // tokens are two 8-pixel rows of the window, so both the cropped main (F of the half) and the 2x2 downsample (same
  // Hrtz order as the finish kernels) come from the wave's own LDS rows; the raw write is skipped when out is null.
  sync_owned_rows();uint l=tid%32,ww=sourcew+2*sx,tx=(window%(ww/8))*8,ty=(window/(ww/8))*8;
  if(main){
   #pragma unroll
   for(uint j=0;j<16;j++){uint tok=first+j;int x=int(tx+tok%8)-int(sx),y=int(ty+tok/8)-int(sy);if(x<0||y<0||x>=int(sourcew)||y>=int(sourceh))continue;uint i=(uint(y)*sourcew+uint(x))*32+l;float v=F(float(scratch.ex[tok*34+l]));
    if constexpr(Main8)reinterpret_cast<unsigned char*>(main)[i]=static_cast<unsigned char>(fp8(v));else main[i]=v;}}
  if(down){
   #pragma unroll
   for(uint k=0;k<4;k++){uint t0=first+2*k;float top=Hrtz(float(scratch.ex[t0*34+l])+float(scratch.ex[(t0+1)*34+l])),bottom=Hrtz(float(scratch.ex[(t0+8)*34+l])+float(scratch.ex[(t0+9)*34+l]));uint x=tx+t0%8,y=ty+t0/8;
    if constexpr(DownCrop){int cx=int(x/2)-int(sx/2),cy=int(y/2)-int(sy/2);if(cx<0||cy<0||cx>=int(sourcew/2)||cy>=int(sourceh/2))continue;down[(uint(cy)*(sourcew/2)+uint(cx))*32+l]=F(Hrtz(Hrtz(top+bottom)*.25f));} // mh_shift_crop of the down grid folded in
    else down[((y/2)*(ww/2)+x/2)*32+l]=F(Hrtz(Hrtz(top+bottom)*.25f));}}
 }
 if constexpr(RgbHead){
  // hip_post_head_fast_half in the epilogue (HLSL DLSS5_C32_EPILOGUE shape): no raw write/read-back, no head dispatch.
  // One lane per token shares feature loads across RGB; each 32-term dot retains its sequential f32 order.
  sync_owned_rows();uint l=tid%32,ww=sourcew+2*sx;
  if(l<16){uint tok=first+l;int x=int((window%(ww/8))*8+tok%8)-int(sx),y=int((window/(ww/8))*8+tok/8)-int(sy);
   if(x>=0&&y>=0&&x<int(sourcew)&&y<int(sourceh)){uint p=uint(y)*sourcew+uint(x);float a0=0.f,a1=0.f,a2=0.f;
    for(uint j=0;j<32;j++){float f=float(scratch.ex[tok*34+j]);a0+=f*headw[j];a1+=f*headw[32+j];a2+=f*headw[64+j];}
    float sums[3]={a0,a1,a2};for(uint row=0;row<3;row++){float acc=Hrtz(sums[row]),centered=color[p*4+row]*.125f-.0625f,v=(acc*rgb_scale+centered)*8.f+.5f;rgb[p*3+row]=clampf(v,0.f,1.f);}
   }
  }
 }
 asm volatile("" ::: "memory");}

}
