// m32-sweep candidate 1: C256 production FFN+QKV (mh_ffn_qkv_body<256,false,true,Mapped,true,true,true,false,true>) with one
// workgroup owning 32 tokens (two 16-token tiles). Every B fragment (expand / contract / project / QKV) feeds two WMMAs, so the
// per-block weight traffic from L2 halves. Each output's K order, activation, rounding, residual init, row sums and byte
// epilogues are the production code's (prod8 = HIP_FFN_LINE_STORES 1: out and norm rows leave as full lines from LDS), per tile.
// Only the production defines are supported (asserted below).
#if !HIP_FFN_TRANSPOSED_TAIL || !HIP_FFN_LINE_STORES || HIP_FFN_WAVE_NORM || HIP_FFN_PK_ACT || HIP_FFN_ABLATE_ACT || HIP_FFN_HOIST_RES!=2
#error "m32 FFN candidate mirrors the production FFN defines only"
#endif
template<bool Mapped>
DEV void m32_ffn_qkv_c256(const float*in,const float*w,unsigned char*out,uint tokens,uint width,uint height,uint workw,uint sx,uint sy,const float*aw,unsigned char*norm){
 constexpr uint C=256;
 const unsigned char*in8=reinterpret_cast<const unsigned char*>(in);
 uint tid=__builtin_amdgcn_workitem_id_x(),wave=tid/32,l=tid%32,rc=l&15,group=l>>4;
 const uint base=__builtin_amdgcn_workgroup_id_x()*32;
 if(base>=tokens)return;
 const bool two=base+16<tokens;
 bool zero[2]={false,!two};
 if constexpr(Mapped){for(uint t=0;t<2;t++){uint first=base+t*16;if(first<tokens&&(first+15<sy*workw||first>=(sy+height)*workw))zero[t]=true;}}
 for(uint t=0;t<2;t++)if(zero[t]&&base+t*16<tokens){uint first=base+t*16;
  for(uint i=tid;i<16*C;i+=2*C)out[first*C+i]=0;
  for(uint i=tid;i<16*3*C;i+=2*C)norm[first*3*C+i]=0;}
 if(zero[0]&&zero[1])return;
 union Storage {unsigned char bytes[2*16*(4*C+4)];float raw[2*16*(C/32)*33];};
 __attribute__((shared)) Storage storage;
 __attribute__((shared)) unsigned char qfeature[2*16*(C+4)];
 __attribute__((shared)) float inverse[2*16*(C/32)];
 constexpr uint NS=C+8;
 __attribute__((shared)) unsigned char nstage[2][2][16*NS];
 auto flush_norm=[&](const unsigned char*st,uint first,uint part){uint row=tid/(C/8),col=(tid%(C/8))*8;unsigned long long v;__builtin_memcpy(&v,st+row*NS+col,8);__builtin_memcpy(norm+((first+row)*3+part)*C+col,&v,8);};
 unsigned char*hid[2]={storage.bytes,storage.bytes+16*(4*C+4)};
 unsigned char*qf[2]={qfeature,qfeature+16*(C+4)};
 const unsigned char*wexp=reinterpret_cast<const unsigned char*>(w);
 // expand: 16x1024 per tile, 64 columns per wave
 f8 e0[4]{},e1[4]{};
 for(uint k=0;k<C;k+=16){
  i2 a0=ffn_input8_fragment<C,Mapped>(in8,base+rc,k+group*8,width,height,workw,sx,sy),a1{};
  if(two)a1=ffn_input8_fragment<C,Mapped>(in8,base+16+rc,k+group*8,width,height,workw,sx,sy);
  for(uint tile=0;tile<4;tile++){uint row=wave*64+tile*16+rc;i2 b=frag_b(wexp,row,C,k,group);
   e0[tile]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a0,b,e0[tile]);e1[tile]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a1,b,e1[tile]);}
 }
 for(uint t=0;t<2;t++){f8*ex=t?e1:e0;unsigned char*hidden=hid[t];
  for(uint tile=0;tile<4;tile++)for(uint e=0;e<8;e++){float a=ex[tile][e],g=clampf(a,-4.f,4.f),q=absf(g)*(-.055908203125f)+.447265625f,poly=g*q+.89453125f;hidden[(group*8+e)*(4*C+4)+wave*64+tile*16+rc]=static_cast<unsigned char>(q8_fused_round(a*poly));}}
 __builtin_amdgcn_s_barrier();
 // grouped contract: each wave 16 columns x its 128-wide K slice
 f8 c0{},c1{};
 {const uint first_k=(wave/2)*128,last_k=first_k+128;const unsigned char*wc=reinterpret_cast<const unsigned char*>(w+4*C*C);
  for(uint k=first_k;k<last_k;k+=16){i2 a0,a1;__builtin_memcpy(&a0,hid[0]+rc*(4*C+4)+k+group*8,8);__builtin_memcpy(&a1,hid[1]+rc*(4*C+4)+k+group*8,8);
   i2 b=frag_b(wc,wave*16+rc,4*C,k,group);c0=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a0,b,c0);c1=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a1,b,c1);}}
 __builtin_amdgcn_s_barrier();
 for(uint e=0;e<8;e++){hid[0][(group*8+e)*(C+4)+wave*16+rc]=static_cast<unsigned char>(q8_fused_round(Hrtz(c0[e])));hid[1][(group*8+e)*(C+4)+wave*16+rc]=static_cast<unsigned char>(q8_fused_round(Hrtz(c1[e])));}
 __builtin_amdgcn_s_barrier();
 // project (transposed tail): residual init per tile, then shared-B WMMAs
 f8 r[2]{};
 for(uint t=0;t<2;t++){float rv[8],rs[8];
  for(uint e=0;e<8;e++){uint c=wave*16+group*8+e;rs[e]=w[9*C*C+c];rv[e]=ffn_input8_nb<C,Mapped>(in8,base+t*16+rc,c,width,height,workw,sx,sy);}
  for(uint e=0;e<8;e++)r[t][e]=Hrtz(rv[e]*rs[e]);}
 {const unsigned char*wp=reinterpret_cast<const unsigned char*>(w+8*C*C);
  for(uint k=0;k<C;k+=16){i2 a0,a1;__builtin_memcpy(&a0,hid[0]+rc*(C+4)+k+group*8,8);__builtin_memcpy(&a1,hid[1]+rc*(C+4)+k+group*8,8);
   i2 b=frag_b(wp,wave*16+rc,C,k,group);r[0]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(b,a0,r[0]);r[1]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(b,a1,r[1]);}}
 for(uint t=0;t<2;t++){uint first=base+t*16;
  for(uint e=0;e<8;e++){uint byte=q8_fused_round(r[t][e]);uint c=wave*16+group*8+e;qf[t][rc*(C+4)+c]=static_cast<unsigned char>(byte);}}
 __builtin_amdgcn_s_barrier();
 for(uint t=0;t<2;t++)if(!zero[t]){uint row=tid/(C/8),col=(tid%(C/8))*8;unsigned long long v;__builtin_memcpy(&v,qf[t]+row*(C+4)+col,8);__builtin_memcpy(out+(base+t*16+row)*C+col,&v,8);}
 // QKV: three parts, shared-B WMMAs; parts 0/1 normalised per head (both tiles' row sums in one round)
 const unsigned char*aq=reinterpret_cast<const unsigned char*>(aw);
 for(uint part=0;part<3;part++){f8 q0{},q1{};
  for(uint k=0;k<C;k+=16){i2 a0,a1;__builtin_memcpy(&a0,qf[0]+rc*(C+4)+k+group*8,8);__builtin_memcpy(&a1,qf[1]+rc*(C+4)+k+group*8,8);
   i2 b=frag_b(aq,part*C+wave*16+rc,C,k,group);q0=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(b,a0,q0);q1=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(b,a1,q1);}
  if(part<2){
   for(uint e=0;e<8;e++){storage.raw[((wave/2)*16+rc)*33+(wave%2)*16+group*8+e]=q0[e];storage.raw[16*(C/32)*33+((wave/2)*16+rc)*33+(wave%2)*16+group*8+e]=q1[e];}
   __builtin_amdgcn_s_barrier();
   if(part==1)for(uint t=0;t<2;t++)if(!zero[t])flush_norm(nstage[t][0],base+t*16,0);
   if(tid<2*16*(C/32)){uint t=tid/(16*(C/32)),i=tid%(16*(C/32)),head=i/16,row=i%16;const float*raw=storage.raw+t*16*(C/32)*33;float ss=0;for(uint k=0;k<32;k++){float v=raw[(head*16+row)*33+k];ss+=v*v;}
    inverse[tid]=__builtin_amdgcn_rsqf(maxf(ss,6.198883056640625e-5f))*(part==0?aw[4*C*C+(C/32)*4096+head]:1.f);}
   __builtin_amdgcn_s_barrier();
  }
  for(uint t=0;t<2;t++){const f8&q=t?q1:q0;float inv=part<2?inverse[t*16*(C/32)+(wave/2)*16+rc]:1.f;unsigned char*st=nstage[t][part==2?1:0];
   for(uint e=0;e<8;e++)st[rc*NS+wave*16+group*8+e]=static_cast<unsigned char>(q8_fused_round(q[e]*inv));}
 }
 WG_FENCE(3);__builtin_amdgcn_s_barrier();WG_FENCE(2);
 for(uint t=0;t<2;t++)if(!zero[t]){flush_norm(nstage[t][0],base+t*16,1);flush_norm(nstage[t][1],base+t*16,2);}
}
KERNEL __attribute__((amdgpu_flat_work_group_size(512,512))) void mh_ffn_fused_c256_frag_project_g128_qkv_bytein_fb_m32(const float*in,const float*w,const float*aw,unsigned char*out,unsigned char*norm,uint tokens,uint width,uint height,uint workw,uint sx,uint sy){m32_ffn_qkv_c256<false>(in,w,out,tokens,width,height,workw,sx,sy,aw,norm);}
KERNEL __attribute__((amdgpu_flat_work_group_size(512,512))) void mh_ffn_fused_c256_frag_project_mapped_g128_qkv_bytein_fb_m32(const float*in,const float*w,const float*aw,unsigned char*out,unsigned char*norm,uint tokens,uint width,uint height,uint workw,uint sx,uint sy){m32_ffn_qkv_c256<true>(in,w,out,tokens,width,height,workw,sx,sy,aw,norm);}
// PDL twins: a group waits for the producer tiles of its 32 tokens and publishes both 16-token tile slots (each wave +1 per
// slot, the same per-slot count as two production groups), so the host's cumulative targets are unchanged.
DEV void m32_pdl_wait(const uint*pflags,uint pepoch,uint pww,uint psx,uint psy,uint tokens,uint width,uint height,uint workw,uint sx,uint sy){
 if(!pflags)return;
 uint tid=__builtin_amdgcn_workitem_id_x(),first=__builtin_amdgcn_workgroup_id_x()*32;
 if(tid<32){uint p=first+tid;if(p<tokens){int x=int(p%workw)-int(sx),y=int(p/workw)-int(sy);
  if(x>=0&&y>=0&&x<int(width)&&y<int(height)){uint idx=((uint(y)+psy)/8)*(pww/8)+(uint(x)+psx)/8;
   while(__hip_atomic_load(pflags+idx,__ATOMIC_RELAXED,__HIP_MEMORY_SCOPE_AGENT)<pepoch)__builtin_amdgcn_s_sleep(1);}}}
 __builtin_amdgcn_s_barrier();
}
DEV void m32_pdl_publish(uint*flags,uint tokens){
 __builtin_amdgcn_fence(__ATOMIC_RELEASE,"agent");
 uint g=__builtin_amdgcn_workgroup_id_x();
 if(__builtin_amdgcn_workitem_id_x()%32==0){__hip_atomic_fetch_add(flags+2*g,1u,__ATOMIC_RELAXED,__HIP_MEMORY_SCOPE_AGENT);if(g*32+16<tokens)__hip_atomic_fetch_add(flags+2*g+1,1u,__ATOMIC_RELAXED,__HIP_MEMORY_SCOPE_AGENT);}
}
KERNEL __attribute__((amdgpu_flat_work_group_size(512,512))) void mh_ffn_fused_c256_frag_project_g128_qkv_bytein_fb_pdl_m32(const float*in,const float*w,const float*aw,unsigned char*out,unsigned char*norm,uint tokens,uint width,uint height,uint workw,uint sx,uint sy,const uint*pflags,uint pepoch,uint pww,uint psx,uint psy,uint*fflags,uint fepoch){m32_pdl_wait(pflags,pepoch,pww,psx,psy,tokens,width,height,workw,sx,sy);m32_ffn_qkv_c256<false>(in,w,out,tokens,width,height,workw,sx,sy,aw,norm);m32_pdl_publish(fflags,tokens);}
KERNEL __attribute__((amdgpu_flat_work_group_size(512,512))) void mh_ffn_fused_c256_frag_project_mapped_g128_qkv_bytein_fb_pdl_m32(const float*in,const float*w,const float*aw,unsigned char*out,unsigned char*norm,uint tokens,uint width,uint height,uint workw,uint sx,uint sy,const uint*pflags,uint pepoch,uint pww,uint psx,uint psy,uint*fflags,uint fepoch){m32_pdl_wait(pflags,pepoch,pww,psx,psy,tokens,width,height,workw,sx,sy);m32_ffn_qkv_c256<true>(in,w,out,tokens,width,height,workw,sx,sy,aw,norm);m32_pdl_publish(fflags,tokens);}
