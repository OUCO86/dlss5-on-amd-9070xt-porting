template<uint C,bool Tiled=false,bool Project=false,bool Mapped=false,bool Grouped=false,bool ByteIn=false,bool ByteFeature=false,bool BatchNorm=false,bool Frag=false>
DEV void mh_ffn_qkv_norm_cost(const float*in,const float*w,unsigned char*out,uint tokens,uint width=0,uint height=0,uint workw=0,uint sx=0,uint sy=0,const float*aw=nullptr,unsigned char*norm=nullptr,uint mode=0,uint repeats=1){
 const unsigned char*in8=reinterpret_cast<const unsigned char*>(in);
 auto load_in=[&](uint row,uint k)->float{if constexpr(ByteIn)return ffn_input8<C,Mapped>(in8,row,k,width,height,workw,sx,sy);else return ffn_input<C,Mapped>(in,row,k,width,height,workw,sx,sy);};
 auto load_in_nb=[&](uint row,uint k)->float{if constexpr(ByteIn)return ffn_input8_nb<C,Mapped>(in8,row,k,width,height,workw,sx,sy);else return ffn_input_nb<C,Mapped>(in,row,k,width,height,workw,sx,sy);};
 uint tid=__builtin_amdgcn_workitem_id_x(),wave=tid/32,l=tid%32,rc=l&15,group=l>>4;
 uint first=__builtin_amdgcn_workgroup_id_x()*16;
 if(first>=tokens)return;
 static_assert(C==128&&ByteIn&&ByteFeature&&!Tiled&&!Frag&&!BatchNorm&&Project&&Grouped,"FFN/QKV requires grouped project");
 union Storage {unsigned char bytes[16*(4*C+4)];float raw[(BatchNorm?2:1)*16*(C/32)*33];};
 __attribute__((shared)) Storage storage;unsigned char*hidden=storage.bytes;
 __attribute__((shared)) unsigned char qfeature[16*(C+4)];
 __attribute__((shared)) float inverse[(BatchNorm?2:1)*16*(C/32)];
 const uint*pw=reinterpret_cast<const uint*>(w);
#if HIP_FFN_COOP_INPUT
 if constexpr(!ByteIn){
#if HIP_FFN_INPUT_PACK4
#if HIP_FFN_HOIST_RES>=2
 // Level 2: the cooperative input staging also loads branch-free (4 window tests per word, loads overlap). Same bytes.
 for(uint i=tid;i<16*(C/4+1);i+=2*C){uint row=i/(C/4+1),k=(i%(C/4+1))*4,word=0;if(k<C){if constexpr(ByteIn)word=ffn_input8_word<C,Mapped>(in8,first+row,k,width,height,workw,sx,sy);else word=pack4(load_in_nb(first+row,k),load_in_nb(first+row,k+1),load_in_nb(first+row,k+2),load_in_nb(first+row,k+3));}__builtin_memcpy(hidden+i*4,&word,4);}
#else
 for(uint i=tid;i<16*(C/4+1);i+=2*C){uint row=i/(C/4+1),k=(i%(C/4+1))*4,word=0;if(k<C){if constexpr(ByteIn)word=ffn_input8_word<C,Mapped>(in8,first+row,k,width,height,workw,sx,sy);else word=pack4(load_in(first+row,k),load_in(first+row,k+1),load_in(first+row,k+2),load_in(first+row,k+3));}__builtin_memcpy(hidden+i*4,&word,4);}
#endif
#else
 for(uint i=tid;i<16*(C+4);i+=2*C){uint row=i/(C+4),k=i%(C+4);hidden[i]=k<C?static_cast<unsigned char>(q8(load_in(first+row,k))):0;}
#endif
 __builtin_amdgcn_s_barrier();
 }
#endif
 f8 expand[4]{};
 for(uint k=0;k<C;k+=16){i2 a{};
#if HIP_FFN_COOP_INPUT
  if constexpr(ByteIn)a=ffn_input8_fragment<C,Mapped>(in8,first+rc,k+group*8,width,height,workw,sx,sy);else __builtin_memcpy(&a,hidden+rc*(C+4)+k+group*8,8);
#else
  for(uint e=0;e<8;e++)pack(a,e,load_in(first+rc,k+group*8+e));
#endif
  for(uint tile=0;tile<4;tile++){uint row=wave*64+tile*16+rc,offset=(row*C+k+group*8)/4;i2 b{};if constexpr(Frag)b=frag_b(reinterpret_cast<const unsigned char*>(w),row,C,k,group);else if constexpr(Tiled){const unsigned char*wb=reinterpret_cast<const unsigned char*>(w);uint off=((row/16)*(C/32)+k/32)*512+(k%32+group*8)*16+row%16;for(uint e=0;e<8;e++)b[e/4]=int(uint(b[e/4])|(uint(wb[off+e*16])<<(8*(e%4))));}else b={int(pw[offset]),int(pw[offset+1])};expand[tile]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,expand[tile]);}
 }
#if HIP_FFN_COOP_INPUT
 // ByteIn reads global memory; only the f32 staging aliases the hidden buffer.
 if constexpr(!ByteIn)__builtin_amdgcn_s_barrier();
#endif
#if HIP_FFN_ABLATE_ACT
 for(uint tile=0;tile<4;tile++)for(uint e=0;e<8;e++)hidden[(group*8+e)*(4*C+4)+wave*64+tile*16+rc]=static_cast<unsigned char>(q8(expand[tile][e])); // timing only
#elif HIP_FFN_PK_ACT==1
 // Exact pairing: two activated values per v_cvt_pk_fp8_f32 (same clamp/RNE per element), the canonical-zero select on the bytes.
 for(uint tile=0;tile<4;tile++)for(uint e=0;e<8;e+=2){float x[2];for(uint j=0;j<2;j++){float a=expand[tile][e+j],g=clampf(a,-4.f,4.f),q=absf(g)*(-.055908203125f)+.447265625f,poly=g*q+.89453125f;x[j]=a*poly;}
  uint two=uint(__builtin_amdgcn_cvt_pk_fp8_f32(__builtin_fminf(__builtin_fmaxf(x[0],-448.f),448.f),__builtin_fminf(__builtin_fmaxf(x[1],-448.f),448.f),0,false));
  for(uint j=0;j<2;j++)hidden[(group*8+e+j)*(4*C+4)+wave*64+tile*16+rc]=static_cast<unsigned char>((bits(x[j])&0x7fffffffu)?(two>>(8*j))&255u:0u);}
#elif HIP_FFN_PK_ACT==2
 // Relaxed (PSNR-gated): the activation polynomial in packed f16 (v_pk_*), two lanes of the 8-vector per instruction;
 // the product a*poly is formed in f16 before the E4M3 cast (f32 in the exact chain), so the byte can differ by one ulp.
 for(uint tile=0;tile<4;tile++)for(uint e=0;e<8;e+=2){h2 a=__builtin_convertvector(f2{expand[tile][e],expand[tile][e+1]},h2);h2 g=__builtin_elementwise_min(__builtin_elementwise_max(a,h2{-4.f,-4.f}),h2{4.f,4.f});h2 q=__builtin_elementwise_abs(g)*h2{-.055908203125f,-.055908203125f}+h2{.447265625f,.447265625f};h2 o=a*(g*q+h2{.89453125f,.89453125f});f2 x=__builtin_convertvector(o,f2);
  uint two=uint(__builtin_amdgcn_cvt_pk_fp8_f32(__builtin_fminf(__builtin_fmaxf(x[0],-448.f),448.f),__builtin_fminf(__builtin_fmaxf(x[1],-448.f),448.f),0,false));
  for(uint j=0;j<2;j++)hidden[(group*8+e+j)*(4*C+4)+wave*64+tile*16+rc]=static_cast<unsigned char>((bits(x[j])&0x7fffffffu)?(two>>(8*j))&255u:0u);}
#else
 for(uint tile=0;tile<4;tile++)for(uint e=0;e<8;e++){float a=expand[tile][e],g=clampf(a,-4.f,4.f),q=absf(g)*(-.055908203125f)+.447265625f,poly=g*q+.89453125f;hidden[(group*8+e)*(4*C+4)+wave*64+tile*16+rc]=static_cast<unsigned char>(q8_fused_round(a*poly));}
#endif
 __builtin_amdgcn_s_barrier();
 f8 accum{};
 const uint first_k=Grouped?(wave/2)*128:0,last_k=Grouped?first_k+128:4*C;
 for(uint k=first_k;k<last_k;k+=16){i2 a;__builtin_memcpy(&a,hidden+rc*(4*C+4)+k+group*8,8);uint offset=4*C*C+((wave*16+rc)*(4*C)+k+group*8)/4;i2 b{};if constexpr(Frag)b=frag_b(reinterpret_cast<const unsigned char*>(w+4*C*C),wave*16+rc,4*C,k,group);else if constexpr(Tiled){const unsigned char*wb=reinterpret_cast<const unsigned char*>(w+4*C*C);uint row=wave*16+rc,off=((row/16)*(4*C/32)+k/32)*512+(k%32+group*8)*16+row%16;for(uint e=0;e<8;e++)b[e/4]=int(uint(b[e/4])|(uint(wb[off+e*16])<<(8*(e%4))));}else b={int(pw[offset]),int(pw[offset+1])};accum=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,accum);}
 if constexpr(Project){
  __builtin_amdgcn_s_barrier();
  for(uint e=0;e<8;e++)hidden[(group*8+e)*(C+4)+wave*16+rc]=static_cast<unsigned char>(q8_fused_round(Hrtz(accum[e])));
  __builtin_amdgcn_s_barrier();
#if HIP_FFN_HOIST_RES
  f8 result{};{const float rs=w[9*C*C+wave*16+rc];float rv[8];
   for(uint e=0;e<8;e++){if constexpr(ByteIn)rv[e]=ffn_input8_nb<C,Mapped>(in8,first+group*8+e,wave*16+rc,width,height,workw,sx,sy);else rv[e]=ffn_input_nb<C,Mapped>(in,first+group*8+e,wave*16+rc,width,height,workw,sx,sy);}
   for(uint e=0;e<8;e++)result[e]=Hrtz(rv[e]*rs);}
#else
  f8 result{};for(uint e=0;e<8;e++)result[e]=Hrtz(load_in(first+group*8+e,wave*16+rc)*w[9*C*C+wave*16+rc]);
#endif
  for(uint k=0;k<C;k+=16){i2 a,b;__builtin_memcpy(&a,hidden+rc*(C+4)+k+group*8,8);uint off=8*C*C+((wave*16+rc)*C+k+group*8)/4;if constexpr(Frag)b=frag_b(reinterpret_cast<const unsigned char*>(w+8*C*C),wave*16+rc,C,k,group);else b={int(pw[off]),int(pw[off+1])};result=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,result);}
  for(uint e=0;e<8;e++){uint byte=q8_fused_round(result[e]);float v=__builtin_amdgcn_cvt_f32_fp8(int(byte),0);if constexpr(ByteFeature)out[(first+group*8+e)*C+wave*16+rc]=static_cast<unsigned char>(byte);else reinterpret_cast<float*>(out)[(first+group*8+e)*C+wave*16+rc]=v;qfeature[(group*8+e)*(C+4)+wave*16+rc]=static_cast<unsigned char>(byte);}
  __builtin_amdgcn_s_barrier();
  const uint*aq=reinterpret_cast<const uint*>(aw);
  if constexpr(BatchNorm){
   f8 q[3]{};
   for(uint part=0;part<3;part++)for(uint k=0;k<C;k+=16){i2 a,b;__builtin_memcpy(&a,qfeature+rc*(C+4)+k+group*8,8);uint off=((part*C+wave*16+rc)*C+k+group*8)/4;if constexpr(Frag)b=frag_b(reinterpret_cast<const unsigned char*>(aw),part*C+wave*16+rc,C,k,group);else b={int(aq[off]),int(aq[off+1])};q[part]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,q[part]);}
   for(uint part=0;part<2;part++)for(uint e=0;e<8;e++)storage.raw[part*16*(C/32)*33+((wave/2)*16+group*8+e)*33+(wave%2)*16+rc]=q[part][e];
   __builtin_amdgcn_s_barrier();
   if(tid<2*16*(C/32)){uint part=tid/(16*(C/32)),t=tid%(16*(C/32)),head=t/16,row=t%16;float ss=0;for(uint k=0;k<32;k++){float v=storage.raw[part*16*(C/32)*33+(head*16+row)*33+k];ss+=v*v;}inverse[tid]=__builtin_amdgcn_rsqf(maxf(ss,6.198883056640625e-5f))*(part==0?aw[4*C*C+(C/32)*4096+head]:1.f);}
   __builtin_amdgcn_s_barrier();
   for(uint part=0;part<3;part++)for(uint e=0;e<8;e++){uint row=group*8+e;float inv=part<2?inverse[part*16*(C/32)+(wave/2)*16+row]:1.f;norm[((first+row)*3+part)*C+wave*16+rc]=static_cast<unsigned char>(q8_fused_round(q[part][e]*inv));}
  }else
  for(uint part=0;part<3;part++){f8 q{};
   for(uint k=0;k<C;k+=16){i2 a,b;__builtin_memcpy(&a,qfeature+rc*(C+4)+k+group*8,8);uint off=((part*C+wave*16+rc)*C+k+group*8)/4;if constexpr(Frag)b=frag_b(reinterpret_cast<const unsigned char*>(aw),part*C+wave*16+rc,C,k,group);else b={int(aq[off]),int(aq[off+1])};q=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,q);}
   if(part<2){
    #pragma clang loop unroll(disable)
    for(uint rep=0;rep<(mode==0?repeats:1u);rep++){
     asm volatile("" ::: "memory");
     for(uint e=0;e<8;e++)storage.raw[((wave/2)*16+group*8+e)*33+(wave%2)*16+rc]=q[e];
     __builtin_amdgcn_s_barrier();
     if(tid<16*(C/32)){
      #pragma clang loop unroll(disable)
      for(uint repa=0;repa<(mode==1?repeats:1u);repa++){
       asm volatile("" ::: "memory");
       uint head=tid/16,row=tid%16;float ss=0;
       for(uint k=0;k<32;k++){float v=storage.raw[(head*16+row)*33+k];ss+=v*v;}
       float inv=__builtin_amdgcn_rsqf(maxf(ss,6.198883056640625e-5f))*(part==0?aw[4*C*C+(C/32)*4096+head]:1.f);
       inverse[tid]=inv;asm volatile("" :: "v"(inv) : "memory");
      }
     }
     __builtin_amdgcn_s_barrier();
    }
    if(mode==2){
     #pragma clang loop unroll(disable)
     for(uint rep=1;rep<repeats;rep++){
      asm volatile("" ::: "memory");__builtin_amdgcn_s_barrier();
      asm volatile("" ::: "memory");__builtin_amdgcn_s_barrier();
     }
    }
   }

   for(uint e=0;e<8;e++){uint row=group*8+e;float inv=part<2?inverse[(wave/2)*16+row]:1.f;norm[((first+row)*3+part)*C+wave*16+rc]=static_cast<unsigned char>(q8_fused_round(q[e]*inv));}
  }
 }else{
 for(uint e=0;e<8;e++)out[(first+group*8+e)*C+wave*16+rc]=static_cast<unsigned char>(q8_fused_round(Hrtz(accum[e])));
 }
}
KERNEL __attribute__((amdgpu_flat_work_group_size(256,256))) void c128_norm_cost(const float*in,const float*w,const float*aw,unsigned char*out,unsigned char*norm,uint tokens,uint width,uint height,uint workw,uint sx,uint sy,uint mode,uint repeats){mh_ffn_qkv_norm_cost<128,false,true,true,true,true,true>(in,w,out,tokens,width,height,workw,sx,sy,aw,norm,mode,repeats);}
