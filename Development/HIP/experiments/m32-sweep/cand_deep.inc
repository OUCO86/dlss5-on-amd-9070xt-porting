// m32-sweep ViT QKV candidates: vit_qkv_project_normalize_fused_f16compact_fp8_frag with one wave owning TM 16-token A tiles x
// TN 16-column B tiles (production TM=1, TN=2 = one head). Per K16 step a lane loads TM A + TN B fragments for TM*TN WMMAs.
// Every output's A conversion, B fragment, K order, per-(tile,head) f16 sum-of-squares WMMA pair, rsqrt/scale and byte store
// are the production kernel's. A second tile is skipped when it starts at or beyond `tokens` (900: 400 tokens = 12.5 x 32).
//   _m32     TM=2 TN=4 (cand 2)    _m32n32  TM=2 TN=2 (cand 3)    _n64  TM=1 TN=4 (cand 4)
template<uint TM,uint TN>
DEV void vit_qkv_frag_tiles(const float*in,const float*w,unsigned char*out,uint tokens,const uint*reuse_gate){if(reuse_gate&&reuse_gate[0])return;
 constexpr uint HEADS=TN/2,COLS=16*TN;
 uint perpart=((tokens+16*TM-1)/(16*TM))*(1024/COLS),part=bid()/perpart,local=bid()%perpart,first=local/(1024/COLS)*(16*TM),row=local%(1024/COLS)*COLS;if(part>=3)return;
 uint live=0;
#pragma unroll
 for(uint t=0;t<TM;t++)live+=first+t*16<tokens;
 f8 acc[TM][TN]{};
 const _Float16*w16=reinterpret_cast<const _Float16*>(w)+part*1048576;
 for(uint k=0;k<1024;k+=16){h8 a[TM];
#pragma unroll
  for(uint t=0;t<TM;t++){a[t]=h8{};if(t<live)for(uint e=0;e<8;e++)a[t][e]=(_Float16)in[(first+t*16+rc())*1024+k+gr()*8+e];}
#pragma unroll
  for(uint j=0;j<TN;j++){h8 b{};__builtin_memcpy(&b,w16+(((row+j*16)/16)*64+k/16)*256+(gr()*16+rc())*8,16);
#pragma unroll
   for(uint t=0;t<TM;t++)acc[t][j]=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(a[t],b,acc[t][j]);}}
 __attribute__((shared)) float raw[TM*HEADS][16*33];
 f8 sum[TM][HEADS]{};
 if(part<2){
#pragma unroll
  for(uint t=0;t<TM;t++)for(uint h=0;h<HEADS;h++)for(uint j=0;j<2;j++)for(uint e=0;e<8;e++)raw[t*HEADS+h][(gr()*8+e)*33+j*16+rc()]=acc[t][h*2+j][e];
  __builtin_amdgcn_s_barrier();
#pragma unroll
  for(uint t=0;t<TM;t++)for(uint h=0;h<HEADS;h++)for(uint k=0;k<32;k+=16){h8 x{},ones{};for(uint e=0;e<8;e++){float v=raw[t*HEADS+h][rc()*33+k+gr()*8+e];x[e]=(_Float16)(v*v);ones[e]=(_Float16)1.f;}sum[t][h]=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(x,ones,sum[t][h]);}
 }
#pragma unroll
 for(uint t=0;t<TM;t++){if(t>=live)continue;
#pragma unroll
  for(uint h=0;h<HEADS;h++){const uint hr=row+h*32;const float scale=part==0?5.65625f*w[1572864+hr/32]:1.f;
#pragma unroll
   for(uint j=0;j<2;j++)for(uint e=0;e<8;e++){float v=acc[t][h*2+j][e];if(part<2){v*=__builtin_amdgcn_rsqf(maxf(sum[t][h][e],6.198883056640625e-5f))*scale;}out[(part*tokens+first+t*16+gr()*8+e)*1024+hr+j*16+rc()]=byte_F(v);}}}
}
WAVE void vit_qkv_project_normalize_fused_f16compact_fp8_frag_m32(const float*in,const float*w,unsigned char*out,uint tokens,const uint*reuse_gate){vit_qkv_frag_tiles<2,4>(in,w,out,tokens,reuse_gate);}
WAVE void vit_qkv_project_normalize_fused_f16compact_fp8_frag_m32n32(const float*in,const float*w,unsigned char*out,uint tokens,const uint*reuse_gate){vit_qkv_frag_tiles<2,2>(in,w,out,tokens,reuse_gate);}
WAVE void vit_qkv_project_normalize_fused_f16compact_fp8_frag_n64(const float*in,const float*w,unsigned char*out,uint tokens,const uint*reuse_gate){vit_qkv_frag_tiles<1,4>(in,w,out,tokens,reuse_gate);}
// m32-sweep ViT projection candidates: vit_project_frag (1024 -> 1024, production = one wave 16 tokens x 16 columns, HIP_VIT_HOIST_SCALE 0)
// with TM 16-token A tiles x TN 16-column B tiles per wave. Per quarter p: acc starts at 0 (p=0: H(skip*scale)), dot8_frag's
// K order within the quarter, then total = p ? total + acc : acc; output F(H(total)). Identical per output.
//   _n32 TM=1 TN=2 (cand 5)   _n64 TM=1 TN=4 (cand 6)   _m32n32 TM=2 TN=2 (cand 7)
template<uint TM,uint TN>
DEV void vit_project_frag_tiles(const float*in,const float*w,const float*skip,float*out,uint tokens,const uint*reuse_gate){if(reuse_gate&&reuse_gate[0])return;
 constexpr uint IN=1024,OUT=1024;
 uint first=bid()/(OUT/(16*TN))*(16*TM),row=bid()%(OUT/(16*TN))*(16*TN);if(first>=tokens)return;
 uint live=0;
#pragma unroll
 for(uint t=0;t<TM;t++)live+=first+t*16<tokens;
 const unsigned char*wf=reinterpret_cast<const unsigned char*>(w);
 f8 total[TM][TN]{};
 for(uint p=0;p<4;p++){f8 a[TM][TN]{};
  if(!p)
#pragma unroll
  for(uint t=0;t<TM;t++)for(uint j=0;j<TN;j++)if(t<live)for(uint e=0;e<8;e++)a[t][j][e]=H(skip[(first+t*16+gr()*8+e)*OUT+row+j*16+rc()]*w[IN*OUT+row+j*16+rc()]);
  for(uint k=p*(IN/4);k<(p+1)*(IN/4);k+=16){i2 x[TM];
#pragma unroll
   for(uint t=0;t<TM;t++){x[t]=i2{};if(t<live)for(uint e=0;e<8;e++)pack(x[t],e,in[(first+t*16+rc())*IN+k+gr()*8+e]);}
#pragma unroll
   for(uint j=0;j<TN;j++){uint r0=row+j*16;i2 y;__builtin_memcpy(&y,wf+((r0/16)*(IN/32)+k/32)*512+((((k%32)/16)*2+gr())*16+rc())*8,8);
#pragma unroll
    for(uint t=0;t<TM;t++)a[t][j]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(x[t],y,a[t][j]);}}
#pragma unroll
  for(uint t=0;t<TM;t++)
#pragma unroll
  for(uint j=0;j<TN;j++)for(uint e=0;e<8;e++)total[t][j][e]=p?total[t][j][e]+a[t][j][e]:a[t][j][e];}
#pragma unroll
 for(uint t=0;t<TM;t++){if(t>=live)continue;for(uint j=0;j<TN;j++)for(uint e=0;e<8;e++)out[(first+t*16+gr()*8+e)*OUT+row+j*16+rc()]=F(H(total[t][j][e]));}
}
WAVE void vit_project_frag_n32(const float*in,const float*w,const float*skip,float*out,uint tokens,uint inputs,uint outputs,const uint*reuse_gate){vit_project_frag_tiles<1,2>(in,w,skip,out,tokens,reuse_gate);}
WAVE void vit_project_frag_n64(const float*in,const float*w,const float*skip,float*out,uint tokens,uint inputs,uint outputs,const uint*reuse_gate){vit_project_frag_tiles<1,4>(in,w,skip,out,tokens,reuse_gate);}
WAVE void vit_project_frag_m32n32(const float*in,const float*w,const float*skip,float*out,uint tokens,uint inputs,uint outputs,const uint*reuse_gate){vit_project_frag_tiles<2,2>(in,w,skip,out,tokens,reuse_gate);}
// m32-sweep decoder candidate (cand 8): decoder_project2x_h16w{,_byteout} with one wave owning 16 tokens x TN 16-column tiles
// (TN = 4, or 2 when outputs == 32). Per part p (4 quarters at inputs 1024, else 1) acc starts at 0, same K order, total = p ?
// total + acc : acc; 2x2 upsample epilogue H(t + F(skip) * scale) per element exactly as production (HIP_DEC_HOIST_SCALE 0).
template<uint TN,bool FullTile,bool ByteOutput>
DEV void decoder_n64_body(const float*in,const float*w,const float*skip,float*out,uint iw,uint ih,uint ow,uint oh,uint inputs,uint outputs){
 uint first=bid()/(outputs/(16*TN))*16,row=bid()%(outputs/(16*TN))*(16*TN);if(first>=iw*ih)return;uint parts=inputs==1024?4:1;f8 total[TN]{};const _Float16*w16=reinterpret_cast<const _Float16*>(w);
 for(uint p=0;p<parts;p++){f8 a[TN]{};for(uint k=p*(inputs/parts);k<(p+1)*(inputs/parts);k+=16){h8 x{};for(uint e=0;e<8;e++){uint j=k+gr()*8+e;x[e]=(FullTile||first+rc()<iw*ih)?(_Float16)in[(first+rc())*inputs+j]:(_Float16)0;}
#pragma unroll
  for(uint c=0;c<TN;c++){h8 y;__builtin_memcpy(&y,w16+(row+c*16+rc())*inputs+k+gr()*8,16);a[c]=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(x,y,a[c]);}}
#pragma unroll
  for(uint c=0;c<TN;c++)for(uint e=0;e<8;e++)total[c][e]=p?total[c][e]+a[c][e]:a[c][e];}
#pragma unroll
 for(uint c=0;c<TN;c++){const uint col=row+c*16+rc();
  for(uint e=0;e<8;e++){uint token=first+gr()*8+e;if(!FullTile&&token>=iw*ih)continue;float t=H(total[c][e]);for(uint dy=0;dy<2;dy++)for(uint dx=0;dx<2;dx++){uint x=(token%iw)*2+dx,y=(token/iw)*2+dy;if(x>=ow||y>=oh)continue;uint i=(y*ow+x)*outputs+col;float merged=H(t+F(skip[i])*w[inputs*outputs+col]);if constexpr(ByteOutput)reinterpret_cast<unsigned char*>(out)[i]=static_cast<unsigned char>(__builtin_amdgcn_cvt_pk_fp8_f32(F(merged),0.f,0,false));else out[i]=outputs==32?merged:F(merged);}}}
}
template<bool ByteOutput>
DEV void decoder_n64_fixed(const float*in,const float*w,const float*skip,float*out,uint iw,uint ih,uint ow,uint oh,uint inputs,uint outputs){
 constexpr uint TN4=4;uint n=iw*ih;
 if(outputs==32){uint first=bid()/(32/(16*2))*16;if(first<n&&n-first>=16)decoder_n64_body<2,true,ByteOutput>(in,w,skip,out,iw,ih,ow,oh,inputs,outputs);else decoder_n64_body<2,false,ByteOutput>(in,w,skip,out,iw,ih,ow,oh,inputs,outputs);return;}
 uint first=bid()/(outputs/(16*TN4))*16;if(first<n&&n-first>=16)decoder_n64_body<4,true,ByteOutput>(in,w,skip,out,iw,ih,ow,oh,inputs,outputs);else decoder_n64_body<4,false,ByteOutput>(in,w,skip,out,iw,ih,ow,oh,inputs,outputs);
}
#define DEC_N64_DISPATCH(BO) if(inputs==1024&&outputs==512)decoder_n64_fixed<BO>(in,w,skip,out,iw,ih,ow,oh,1024,512);else if(inputs==512&&outputs==256)decoder_n64_fixed<BO>(in,w,skip,out,iw,ih,ow,oh,512,256);else if(inputs==256&&outputs==128)decoder_n64_fixed<BO>(in,w,skip,out,iw,ih,ow,oh,256,128);else if(inputs==128&&outputs==64)decoder_n64_fixed<BO>(in,w,skip,out,iw,ih,ow,oh,128,64);else if(inputs==64&&outputs==32)decoder_n64_fixed<BO>(in,w,skip,out,iw,ih,ow,oh,64,32);else decoder_n64_fixed<BO>(in,w,skip,out,iw,ih,ow,oh,inputs,outputs);
WAVE void decoder_project2x_h16w_n64(const float*in,const float*w,const float*skip,float*out,uint iw,uint ih,uint ow,uint oh,uint inputs,uint outputs){DEC_N64_DISPATCH(false)}
WAVE void decoder_project2x_h16w_byteout_n64(const float*in,const float*w,const float*skip,float*out,uint iw,uint ih,uint ow,uint oh,uint inputs,uint outputs){DEC_N64_DISPATCH(true)}
