// Candidate (c512-ffn mode 5): mh_qkv_normalize_frag_c512 with the byte epilogue staged through a wave-private LDS
// tile. Production issues 32 global_store_b8 per lane (1024 per wave); here the same q8(F(acc*inv)) bytes are written to a
// 16-row x 64-byte LDS tile and each lane stores 32 contiguous bytes of one row with two 128-bit stores. Matrix, row
// sums, inv and the output layout [token][1536] are unchanged, so the output is identical by construction.
using c5u4=unsigned __attribute__((ext_vector_type(4)));
FASTWAVE void mh_qkv_normalize_frag_c512_wide(const unsigned char*in8,const float*w,unsigned char*out,uint tokens){
 const uint C=512,N=1536;uint l=__builtin_amdgcn_workitem_id_x(),rc=l&15,g=l>>4,block=__builtin_amdgcn_workgroup_id_x(),first=block/24*16,col=block%24*64;if(first>=tokens)return;
 const unsigned char*wb=reinterpret_cast<const unsigned char*>(w);f8 acc[4]{};
 for(uint gs=0;gs<16;gs++){const unsigned char*atile=in8+((first/16)*16+gs)*512+rc*32+g*8;
  for(uint h=0;h<2;h++){i2 a;__builtin_memcpy(&a,atile+h*16,8);
   for(uint n=0;n<4;n++){uint n0=col+n*16+rc;i2 b;__builtin_memcpy(&b,wb+((n0/16)*16+gs)*512+((h*2+g)*16+n0%16)*8,8);acc[n]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,acc[n]);}}}
 __attribute__((shared)) float raw[17*65];
 __attribute__((shared)) c5u4 tile[16*4];
 for(uint n=0;n<4;n++)for(uint e=0;e<8;e++)raw[(g*8+e)*65+n*16+rc]=acc[n][e];
 WG_FENCE(3);__builtin_amdgcn_s_barrier();WG_FENCE(2);
 uint part=col/C,head0=(col%C)/32,scale=4*C*C+(C/32)*4096;
 {uint row=l%16,h=l/16;float inv=1.f;if(first+row<tokens&&part<2){float ss=0.f;for(uint j=0;j<32;j++){float v=raw[row*65+h*32+j];ss+=v*v;}inv=__builtin_amdgcn_rsqf(maxf(ss,6.198883056640625e-5f))*(part==0?w[scale+head0+h]:1.f);}raw[16*65+l]=inv;}
 WG_FENCE(3);__builtin_amdgcn_s_barrier();WG_FENCE(2);
 unsigned char*tb=reinterpret_cast<unsigned char*>(tile);
 for(uint n=0;n<4;n++)for(uint e=0;e<8;e++){uint row=g*8+e;tb[row*64+n*16+rc]=static_cast<unsigned char>(q8(F(acc[n][e]*raw[16*65+(n/2)*16+row])));}
 WG_FENCE(3);__builtin_amdgcn_s_barrier();WG_FENCE(2);
 {uint row=l>>1,half=l&1,p=first+row;if(p<tokens){c5u4*d=reinterpret_cast<c5u4*>(out+size_t(p)*N+col+half*32);d[0]=tile[row*4+half*2];d[1]=tile[row*4+half*2+1];}}
}

// Candidate (c512-ffn mode 6): as mode 5, but one wave owns 32 tokens (two 16-token A tiles) x 64 columns, so every B
// fragment load feeds two WMMAs (weight L2 traffic halved). Each output's K accumulation order is unchanged; the
// 16-row epilogue (row sums, inv, q8 bytes, 128-bit stores) runs once per tile in the same form as mode 5. The second
// tile is skipped when it starts at or beyond `tokens` (900: 6000 tokens = 187.5 x 32).
FASTWAVE void mh_qkv_normalize_frag_c512_m32(const unsigned char*in8,const float*w,unsigned char*out,uint tokens){
 const uint C=512,N=1536;uint l=__builtin_amdgcn_workitem_id_x(),rc=l&15,g=l>>4,block=__builtin_amdgcn_workgroup_id_x(),first=block/24*32,col=block%24*64;if(first>=tokens)return;
 const bool two=first+16<tokens;
 const unsigned char*wb=reinterpret_cast<const unsigned char*>(w);f8 acc0[4]{},acc1[4]{};
 for(uint gs=0;gs<16;gs++){const unsigned char*t0=in8+((first/16)*16+gs)*512+rc*32+g*8,*t1=t0+16*512;
  for(uint h=0;h<2;h++){i2 a0,a1{};__builtin_memcpy(&a0,t0+h*16,8);if(two)__builtin_memcpy(&a1,t1+h*16,8);
   for(uint n=0;n<4;n++){uint n0=col+n*16+rc;i2 b;__builtin_memcpy(&b,wb+((n0/16)*16+gs)*512+((h*2+g)*16+n0%16)*8,8);
    acc0[n]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a0,b,acc0[n]);acc1[n]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a1,b,acc1[n]);}}}
 __attribute__((shared)) float raw[17*65];
 __attribute__((shared)) c5u4 tile[16*4];
 unsigned char*tb=reinterpret_cast<unsigned char*>(tile);
 uint part=col/C,head0=(col%C)/32,scale=4*C*C+(C/32)*4096;
 for(uint t=0;t<2;t++){if(t&&!two)break;const uint base=first+t*16;f8*acc=t?acc1:acc0;
  if(t){WG_FENCE(3);__builtin_amdgcn_s_barrier();WG_FENCE(2);}
  for(uint n=0;n<4;n++)for(uint e=0;e<8;e++)raw[(g*8+e)*65+n*16+rc]=acc[n][e];
  WG_FENCE(3);__builtin_amdgcn_s_barrier();WG_FENCE(2);
  {uint row=l%16,h=l/16;float inv=1.f;if(base+row<tokens&&part<2){float ss=0.f;for(uint j=0;j<32;j++){float v=raw[row*65+h*32+j];ss+=v*v;}inv=__builtin_amdgcn_rsqf(maxf(ss,6.198883056640625e-5f))*(part==0?w[scale+head0+h]:1.f);}raw[16*65+l]=inv;}
  WG_FENCE(3);__builtin_amdgcn_s_barrier();WG_FENCE(2);
  for(uint n=0;n<4;n++)for(uint e=0;e<8;e++){uint row=g*8+e;tb[row*64+n*16+rc]=static_cast<unsigned char>(q8(F(acc[n][e]*raw[16*65+(n/2)*16+row])));}
  WG_FENCE(3);__builtin_amdgcn_s_barrier();WG_FENCE(2);
  {uint row=l>>1,half=l&1,p=base+row;if(p<tokens){c5u4*d=reinterpret_cast<c5u4*>(out+size_t(p)*N+col+half*32);d[0]=tile[row*4+half*2];d[1]=tile[row*4+half*2+1];}}
 }
}

// Generalised (c512-ffn modes 7/8): T 16-token tiles per wave (T=4: 64 tokens), each B fragment feeds T WMMAs. Tiles at
// or beyond `tokens` load no A and are skipped in the epilogue; per-output K order and the epilogue are unchanged.
template<uint T>
DEV void qkv_frag_c512_tiles(const unsigned char*in8,const float*w,unsigned char*out,uint tokens){
 const uint C=512,N=1536;uint l=__builtin_amdgcn_workitem_id_x(),rc=l&15,g=l>>4,block=__builtin_amdgcn_workgroup_id_x(),first=block/24*(16*T),col=block%24*64;if(first>=tokens)return;
 const uint live=(tokens-first+15)/16<T?(tokens-first+15)/16:T;
 const unsigned char*wb=reinterpret_cast<const unsigned char*>(w);f8 acc[T][4]{};
 for(uint gs=0;gs<16;gs++){const unsigned char*t0=in8+((first/16)*16+gs)*512+rc*32+g*8;
  for(uint h=0;h<2;h++){i2 a[T];
#pragma unroll
   for(uint t=0;t<T;t++){a[t]=i2{};if(t<live)__builtin_memcpy(&a[t],t0+t*16*512+h*16,8);}
   for(uint n=0;n<4;n++){uint n0=col+n*16+rc;i2 b;__builtin_memcpy(&b,wb+((n0/16)*16+gs)*512+((h*2+g)*16+n0%16)*8,8);
#pragma unroll
    for(uint t=0;t<T;t++)acc[t][n]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a[t],b,acc[t][n]);}}}
 __attribute__((shared)) float raw[17*65];
 __attribute__((shared)) c5u4 tile[16*4];
 unsigned char*tb=reinterpret_cast<unsigned char*>(tile);
 uint part=col/C,head0=(col%C)/32,scale=4*C*C+(C/32)*4096;
#pragma unroll
 for(uint t=0;t<T;t++){if(t>=live)break;const uint base=first+t*16;
  if(t){WG_FENCE(3);__builtin_amdgcn_s_barrier();WG_FENCE(2);}
  for(uint n=0;n<4;n++)for(uint e=0;e<8;e++)raw[(g*8+e)*65+n*16+rc]=acc[t][n][e];
  WG_FENCE(3);__builtin_amdgcn_s_barrier();WG_FENCE(2);
  {uint row=l%16,h=l/16;float inv=1.f;if(base+row<tokens&&part<2){float ss=0.f;for(uint j=0;j<32;j++){float v=raw[row*65+h*32+j];ss+=v*v;}inv=__builtin_amdgcn_rsqf(maxf(ss,6.198883056640625e-5f))*(part==0?w[scale+head0+h]:1.f);}raw[16*65+l]=inv;}
  WG_FENCE(3);__builtin_amdgcn_s_barrier();WG_FENCE(2);
  for(uint n=0;n<4;n++)for(uint e=0;e<8;e++){uint row=g*8+e;tb[row*64+n*16+rc]=static_cast<unsigned char>(q8(F(acc[t][n][e]*raw[16*65+(n/2)*16+row])));}
  WG_FENCE(3);__builtin_amdgcn_s_barrier();WG_FENCE(2);
  {uint row=l>>1,half=l&1,p=base+row;if(p<tokens){c5u4*d=reinterpret_cast<c5u4*>(out+size_t(p)*N+col+half*32);d[0]=tile[row*4+half*2];d[1]=tile[row*4+half*2+1];}}
 }
}
FASTWAVE void mh_qkv_normalize_frag_c512_m48(const unsigned char*in8,const float*w,unsigned char*out,uint tokens){qkv_frag_c512_tiles<3>(in8,w,out,tokens);}
FASTWAVE void mh_qkv_normalize_frag_c512_m64(const unsigned char*in8,const float*w,unsigned char*out,uint tokens){qkv_frag_c512_tiles<4>(in8,w,out,tokens);}
