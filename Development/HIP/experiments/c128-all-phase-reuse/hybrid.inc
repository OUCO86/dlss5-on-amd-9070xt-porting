// C128: one wave owns both 16-row tiles throughout the fused pipeline.
// All B fragments are shared across these row tiles, preserving each K reduction.
template<bool Mapped,bool ByteIn,bool ByteFeature>
DEV void mh_ffn_qkv_rows2(const float*in,const float*w,const float*aw,unsigned char*out,unsigned char*norm,uint tokens,uint width,uint height,uint workw,uint sx,uint sy){
 constexpr uint C=128;
 const uint tid=__builtin_amdgcn_workitem_id_x(),wave=tid/32,l=tid%32,rc=l&15,g=l>>4;
 const bool active=wave<8;
 const uint first=__builtin_amdgcn_workgroup_id_x()*32;
 if(first>=tokens)return;
 const auto*in8=reinterpret_cast<const unsigned char*>(in);
 const auto*pw=reinterpret_cast<const uint*>(w);const auto*aq=reinterpret_cast<const uint*>(aw);
 union Storage{unsigned char bytes[32*516];float raw[4*32*33];};
 __attribute__((shared)) Storage storage;
 __attribute__((shared)) unsigned char feature[32*132];
 __attribute__((shared)) float inverse[4*32];
 auto*hidden=storage.bytes;
 if constexpr(!ByteIn){
  for(uint i=tid;i<32*33;i+=512){uint row=i/33,k=(i%33)*4,v=0;
   if(k<C)v=pack4(ffn_input_nb<C,Mapped>(in,first+row,k,width,height,workw,sx,sy),ffn_input_nb<C,Mapped>(in,first+row,k+1,width,height,workw,sx,sy),ffn_input_nb<C,Mapped>(in,first+row,k+2,width,height,workw,sx,sy),ffn_input_nb<C,Mapped>(in,first+row,k+3,width,height,workw,sx,sy));
   __builtin_memcpy(hidden+i*4,&v,4);
  }
  __builtin_amdgcn_s_barrier();
 }
 f8 expand[2][2]{};
 for(uint k=0;k<C;k+=16){i2 a[2];
  for(uint r=0;r<2;r++){
   if constexpr(ByteIn)a[r]=ffn_input8_fragment<C,Mapped>(in8,first+r*16+rc,k+g*8,width,height,workw,sx,sy);
   else __builtin_memcpy(&a[r],hidden+(r*16+rc)*132+k+g*8,8);
  }
  for(uint t=0;t<2;t++){uint off=((wave*32+t*16+rc)*C+k+g*8)/4;i2 b{int(pw[off]),int(pw[off+1])};
   for(uint r=0;r<2;r++)expand[r][t]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a[r],b,expand[r][t]);
  }
 }
 if constexpr(!ByteIn)__builtin_amdgcn_s_barrier();
 for(uint r=0;r<2;r++)for(uint t=0;t<2;t++)for(uint e=0;e<8;e++){
  float a=expand[r][t][e],v=clampf(a,-4.f,4.f),q=absf(v)*(-.055908203125f)+.447265625f,poly=v*q+.89453125f;
  hidden[(r*16+g*8+e)*516+wave*32+t*16+rc]=static_cast<unsigned char>(q8_fused_round(a*poly));
 }
 __builtin_amdgcn_s_barrier();
 f8 contract[2]{};
 if(active)for(uint k=(wave/2)*128;k<(wave/2+1)*128;k+=16){uint off=4*C*C+((wave*16+rc)*512+k+g*8)/4;i2 b{int(pw[off]),int(pw[off+1])};
  for(uint r=0;r<2;r++){i2 a;__builtin_memcpy(&a,hidden+(r*16+rc)*516+k+g*8,8);contract[r]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,contract[r]);}
 }
 __builtin_amdgcn_s_barrier();
 if(active)for(uint r=0;r<2;r++)for(uint e=0;e<8;e++)hidden[(r*16+g*8+e)*132+wave*16+rc]=static_cast<unsigned char>(q8_fused_round(Hrtz(contract[r][e])));
 __builtin_amdgcn_s_barrier();
 f8 result[2]{};const float scale=active?w[9*C*C+wave*16+rc]:0.f;
 if(active)for(uint r=0;r<2;r++)for(uint e=0;e<8;e++){
  float v;if constexpr(ByteIn)v=ffn_input8_nb<C,Mapped>(in8,first+r*16+g*8+e,wave*16+rc,width,height,workw,sx,sy);
  else v=ffn_input_nb<C,Mapped>(in,first+r*16+g*8+e,wave*16+rc,width,height,workw,sx,sy);
  result[r][e]=Hrtz(v*scale);
 }
 if(active)for(uint k=0;k<C;k+=16){uint off=8*C*C+((wave*16+rc)*C+k+g*8)/4;i2 b{int(pw[off]),int(pw[off+1])};
  for(uint r=0;r<2;r++){i2 a;__builtin_memcpy(&a,hidden+(r*16+rc)*132+k+g*8,8);result[r]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,result[r]);}
 }
 if(active)for(uint r=0;r<2;r++)for(uint e=0;e<8;e++){uint row=r*16+g*8+e,byte=q8_fused_round(result[r][e]);
  if constexpr(ByteFeature)out[(first+row)*C+wave*16+rc]=static_cast<unsigned char>(byte);
  else reinterpret_cast<float*>(out)[(first+row)*C+wave*16+rc]=__builtin_amdgcn_cvt_f32_fp8(int(byte),0);
  feature[row*132+wave*16+rc]=static_cast<unsigned char>(byte);
 }
 __builtin_amdgcn_s_barrier();
 for(uint part=0;part<3;part++){f8 q[2]{};
  if(active)for(uint k=0;k<C;k+=16){uint off=((part*C+wave*16+rc)*C+k+g*8)/4;i2 b{int(aq[off]),int(aq[off+1])};
   for(uint r=0;r<2;r++){i2 a;__builtin_memcpy(&a,feature+(r*16+rc)*132+k+g*8,8);q[r]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,q[r]);}
  }
  if(part<2){
   if(active)for(uint r=0;r<2;r++)for(uint e=0;e<8;e++)storage.raw[((wave/2)*32+r*16+g*8+e)*33+(wave%2)*16+rc]=q[r][e];
   __builtin_amdgcn_s_barrier();
   if(tid<128){uint head=tid/32,row=tid%32;float ss=0;for(uint k=0;k<32;k++){float v=storage.raw[(head*32+row)*33+k];ss+=v*v;}inverse[tid]=__builtin_amdgcn_rsqf(maxf(ss,6.198883056640625e-5f))*(part==0?aw[4*C*C+4*4096+head]:1.f);}
   __builtin_amdgcn_s_barrier();
  }
  if(active)for(uint r=0;r<2;r++)for(uint e=0;e<8;e++){uint row=r*16+g*8+e;float inv=part<2?inverse[(wave/2)*32+row]:1.f;norm[((first+row)*3+part)*C+wave*16+rc]=static_cast<unsigned char>(q8_fused_round(q[r][e]*inv));}
 }
}
