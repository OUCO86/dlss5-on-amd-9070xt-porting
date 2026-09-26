// c512-ffn deep candidates: split_projection_frag and split_mix_blocked_h16w with one wave owning 32 tokens (two 16-token
// A tiles) x 64 columns, so each B fragment feeds two WMMAs. Per-output initial value, K order and epilogue are those of
// the production kernels; the second tile is skipped when it starts at/after `tokens`.
WAVE void split_projection_frag_m32(const unsigned char*in8,const float*w,const float*skip,float*out,unsigned char*out8,uint tokens){
 uint first=bid()/8*32,row=bid()%8*64;if(first>=tokens)return;const bool two=first+16<tokens;f8 acc[2][4]{};
 for(uint t=0;t<2;t++){if(t&&!two)break;for(uint j=0;j<4;j++)for(uint e=0;e<8;e++)acc[t][j][e]=H(skip[(first+t*16+gr()*8+e)*512+row+j*16+rc()]*w[262144+row+j*16+rc()]);}
 const unsigned char*wb=reinterpret_cast<const unsigned char*>(w);const unsigned char*arow=in8+((first/16)*16)*512+rc()*32+gr()*8;
 for(uint gs=0;gs<16;gs++)for(uint h=0;h<2;h++){i2 a0,a1{};__builtin_memcpy(&a0,arow+gs*512+h*16,8);if(two)__builtin_memcpy(&a1,arow+16*512+gs*512+h*16,8);
  for(uint j=0;j<4;j++){uint n0=row+j*16+rc();i2 b;__builtin_memcpy(&b,wb+((n0/16)*16+gs)*512+((h*2+gr())*16+n0%16)*8,8);
   acc[0][j]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a0,b,acc[0][j]);acc[1][j]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a1,b,acc[1][j]);}}
 for(uint t=0;t<2;t++){if(t&&!two)break;for(uint j=0;j<4;j++)for(uint e=0;e<8;e++){uint r=first+t*16+gr()*8+e,c=row+j*16+rc();float v=F(H(acc[t][j][e]));out[r*512+c]=v;out8[((r/16)*16+c/32)*512+(r%16)*32+c%32]=static_cast<unsigned char>(__builtin_amdgcn_cvt_pk_fp8_f32(v,0.f,0,false));}}
}
WAVE void split_mix_blocked_h16w_m32(const float*in,const float*w,float*out,uint tokens){
 uint first=bid()/8*32,row=bid()%8*64;if(first>=tokens)return;const bool two=first+16<tokens;f8 acc0[4]{},acc1[4]{};const _Float16*w16=reinterpret_cast<const _Float16*>(w);
 for(uint k=0;k<512;k+=16){h8 a0{},a1{};for(uint e=0;e<8;e++)a0[e]=(_Float16)in[(first+rc())*512+k+gr()*8+e];if(two)for(uint e=0;e<8;e++)a1[e]=(_Float16)in[(first+16+rc())*512+k+gr()*8+e];
  for(uint j=0;j<4;j++){h8 b;__builtin_memcpy(&b,w16+(row+j*16+rc())*512+k+gr()*8,16);acc0[j]=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(a0,b,acc0[j]);acc1[j]=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(a1,b,acc1[j]);}}
 for(uint j=0;j<4;j++)for(uint e=0;e<8;e++)out[(first+gr()*8+e)*512+row+j*16+rc()]=F(Hrtz(acc0[j][e]));
 if(two)for(uint j=0;j<4;j++)for(uint e=0;e<8;e++)out[(first+16+gr()*8+e)*512+row+j*16+rc()]=F(Hrtz(acc1[j][e]));
}
