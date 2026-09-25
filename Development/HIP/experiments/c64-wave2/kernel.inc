// Independent two-wave C64 block. Each wave owns all 64 tokens of one 32-channel head.
// Shared matrices use native 16x16 A fragments: [token tile][channel tile][lane][8 bytes].
// Two 4 KiB planes alternate input -> contract -> feature -> AV; no global intermediate.
DEV uint w2_lane(){return __builtin_amdgcn_workitem_id_x()&31u;}
DEV uint w2_rc(){return w2_lane()&15u;}
DEV uint w2_gr(){return w2_lane()>>4;}
DEV uint w2_pixel(uint win,uint tok,uint workw){return ((win/(workw/8))*8+tok/8)*workw+(win%(workw/8))*8+tok%8;}
DEV void w2_sync(){WG_FENCE(3);__builtin_amdgcn_s_barrier();WG_FENCE(2);}
DEV i2 w2_load(const unsigned char*p,uint qt,uint ct){i2 a;__builtin_memcpy(&a,p+((qt*4+ct)*32+w2_lane())*8,8);return a;}
DEV void w2_store(unsigned char*p,uint qt,uint ct,i2 a){__builtin_memcpy(p+((qt*4+ct)*32+w2_lane())*8,&a,8);}
DEV i2 w2_weight(const float*p,uint row,uint stride,uint k){i2 a;__builtin_memcpy(&a,reinterpret_cast<const unsigned char*>(p)+row*stride+k+w2_gr()*8,8);return a;}
DEV void w2_bits(i2&a,uint e,uint v){a[e/4]=int(uint(a[e/4])|((v&255u)<<(8*(e%4))));}
DEV float w2_shuffle(float v,uint src){return __builtin_bit_cast(float,__builtin_amdgcn_ds_bpermute(src*4,__builtin_bit_cast(int,v)));}
DEV float w2_serial_norm(f8 lo,f8 hi){
 // Same 32 scalar products/adds in channel order as production. Both halves execute;
 // each shuffle carries the correct prefix to the half owning the next eight channels.
 float s=0.f;
 _Pragma("unroll 8") for(uint e=0;e<8;e++)s+=lo[e]*lo[e];
 s=w2_shuffle(s,w2_rc());
 _Pragma("unroll 8") for(uint e=0;e<8;e++)s+=lo[e]*lo[e];
 s=w2_shuffle(s,w2_rc()+16);
 _Pragma("unroll 8") for(uint e=0;e<8;e++)s+=hi[e]*hi[e];
 s=w2_shuffle(s,w2_rc());
 _Pragma("unroll 8") for(uint e=0;e<8;e++)s+=hi[e]*hi[e];
 return w2_shuffle(s,w2_rc()+16);
}

template<bool ByteIn,bool ByteOut>
DEV void c64_wave2_body(const float*in,const float*fw,const float*aw,void*out_any,
 uint width,uint height,uint workw,uint workh,uint sx,uint sy,uint post){
 const uint win=__builtin_amdgcn_workgroup_id_x(),head=__builtin_amdgcn_workitem_id_x()/32;
 const uint rc=w2_rc(),gr=w2_gr();
 if(win>=(workw/8)*(workh/8))return;
 __attribute__((shared)) unsigned char plane0[4096],plane1[4096];
 auto input=[&](uint tok,uint col)->float{
  uint p=w2_pixel(win,tok,workw);int x=int(p%workw)-int(sx),y=int(p/workw)-int(sy);
  bool valid=x>=0&&y>=0&&x<int(width)&&y<int(height);uint idx=valid?(uint(y)*width+uint(x))*64+col:col;
  float v;if constexpr(ByteIn)v=__builtin_amdgcn_cvt_f32_fp8(int(reinterpret_cast<const unsigned char*>(in)[idx]),0);else v=in[idx];
  return valid?v:0.f;
 };
 // Stage original input in A fragments. Preserve the byte cast used by pack4.
 for(uint qt=0;qt<4;qt++)for(uint ci=0;ci<2;ci++){
  i2 a{};for(uint e=0;e<8;e++)w2_bits(a,e,q8(input(qt*16+rc,head*32+ci*16+gr*8+e)));
  w2_store(plane0,qt,head*2+ci,a);
 }
 w2_sync();
 // Each head contracts only its own 128 hidden channels. Expanded fragments never enter LDS.
 _Pragma("clang loop unroll(disable)") for(uint qt=0;qt<4;qt++){
  f8 contract[2]{};
  _Pragma("clang loop unroll(disable)") for(uint ht=0;ht<8;ht++){
   f8 expanded{};
   for(uint kt=0;kt<4;kt++){
    i2 a=w2_load(plane0,qt,kt),b=w2_weight(fw,head*128+ht*16+rc,64,kt*16);
    expanded=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(b,a,expanded);
   }
   i2 hidden{};
   for(uint e=0;e<8;e++){float a=expanded[e],g=clampf(a,-4.f,4.f),q=absf(g)*(-.055908203125f)+.447265625f,poly=g*q+.89453125f;w2_bits(hidden,e,q8_fused_round(a*poly));}
   for(uint ci=0;ci<2;ci++){
    i2 b=w2_weight(fw+4*64*64,head*32+ci*16+rc,256,head*128+ht*16);
    contract[ci]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(b,hidden,contract[ci]);
   }
  }
  for(uint ci=0;ci<2;ci++){i2 a{};for(uint e=0;e<8;e++)w2_bits(a,e,q8_fused_round(Hrtz(contract[ci][e])));w2_store(plane1,qt,head*2+ci,a);}
 }
 w2_sync();
 // Cross-head FFN mixing plus the original residual. plane0 is now free for feature bytes.
 _Pragma("clang loop unroll(disable)") for(uint qt=0;qt<4;qt++){
  f8 result[2]{};
  for(uint ci=0;ci<2;ci++)for(uint e=0;e<8;e++){uint c=head*32+ci*16+gr*8+e;result[ci][e]=Hrtz(input(qt*16+rc,c)*fw[9*64*64+c]);}
  for(uint kt=0;kt<4;kt++)for(uint ci=0;ci<2;ci++){
   i2 a=w2_load(plane1,qt,kt),b=w2_weight(fw+8*64*64,head*32+ci*16+rc,64,kt*16);
   result[ci]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(b,a,result[ci]);
  }
  for(uint ci=0;ci<2;ci++){i2 a{};for(uint e=0;e<8;e++)w2_bits(a,e,q8_fused_round(result[ci][e]));w2_store(plane0,qt,head*2+ci,a);}
 }
 w2_sync();
 // Q/K use A-fragment orientation. V is computed in the opposite orientation,
 // directly becoming the B fragments consumed by P*V; no V transpose/staging needed.
 i2 qkv[3][4][2];
 _Pragma("unroll 3") for(uint part=0;part<3;part++){
  _Pragma("unroll 4") for(uint qt=0;qt<4;qt++){
   f8 q[2]{};
   for(uint kt=0;kt<4;kt++)for(uint ci=0;ci<2;ci++){
    i2 a=w2_load(plane0,qt,kt),b=w2_weight(aw,part*64+head*32+ci*16+rc,64,kt*16);
    if(part<2)q[ci]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(b,a,q[ci]);
    else q[ci]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,q[ci]);
   }
   float inv=1.f;
   if(part<2){float ss=w2_serial_norm(q[0],q[1]);inv=__builtin_amdgcn_rsqf(maxf(ss,6.198883056640625e-5f))*(part==0?aw[4*64*64+2*4096+head]:1.f);}
   for(uint ci=0;ci<2;ci++){i2 a{};for(uint e=0;e<8;e++)w2_bits(a,e,q8_fused_round(q[ci][e]*inv));qkv[part][qt][ci]=a;}
  }
 }
 // One wave owns all keys and queries of a head. Existing WMMA half row-sum order is retained.
 _Pragma("unroll 4") for(uint qt=0;qt<4;qt++){
  h8 exponent[4];
  _Pragma("unroll 4") for(uint key=0;key<4;key++){
   f8 scores{};
   _Pragma("unroll 2") for(uint ci=0;ci<2;ci++)scores=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(qkv[1][key][ci],qkv[0][qt][ci],scores);
   h8 ex{};
   for(uint e=0;e<8;e++){
    uint row=qt*16+rc,k=key*16+gr*8+e;
    float score=scores[e]+aw[4*64*64+head*4096+row*64+k],affine=clampf(score*.044921875f+1.30078125f,1.03125f,1.5693359375f);
    uint ah=(bits(affine)>>13)-0x1c000u;unsigned short hb=static_cast<unsigned short>(((ah<<5)+0x8000u)&65535u);ex[e]=__builtin_bit_cast(_Float16,hb);
   }
   exponent[key]=ex;
  }
  h8 ones{};for(uint e=0;e<8;e++)ones[e]=(_Float16)1.f;
  f8 sums[2]{};
  _Pragma("unroll 2") for(uint side=0;side<2;side++){
   _Pragma("unroll 2") for(uint half=0;half<2;half++)sums[side]=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(ones,exponent[side+2*half],sums[side]);
  }
  i2 prob[4];
  _Pragma("unroll 4") for(uint key=0;key<4;key++){i2 a{};for(uint e=0;e<8;e++){float inv=1.f/(sums[0][e]+sums[1][e]);w2_bits(a,e,q8_fused_round(float(exponent[key][e])*inv));}prob[key]=a;}
  for(uint ci=0;ci<2;ci++){
   f8 av{};
   _Pragma("unroll 4") for(uint key=0;key<4;key++)av=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(qkv[2][key][ci],prob[key],av);
   i2 a{};for(uint e=0;e<8;e++)w2_bits(a,e,q8_fused_round(av[e]));w2_store(plane1,qt,head*2+ci,a);
  }
 }
 w2_sync();
 // All heads' AV ready; feature still lives in plane0. Preserve diagonal residual and K order.
 const unsigned char*diag=reinterpret_cast<const unsigned char*>(aw)+4*(4*64*64+2*4096+2+64);
 _Pragma("clang loop unroll(disable)") for(uint qt=0;qt<4;qt++){
  f8 result[2]{};
  for(uint ci=0;ci<2;ci++){
   uint ct=head*2+ci;i2 a=w2_load(plane0,qt,ct);
   for(uint part=0;part<3;part++){i2 b;__builtin_memcpy(&b,diag+(part*4+ct)*512+(gr*16+rc)*8,8);result[ci]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(b,a,result[ci]);}
  }
  for(uint kt=0;kt<4;kt++)for(uint ci=0;ci<2;ci++){
   i2 a=w2_load(plane1,qt,kt),b=w2_weight(aw+3*64*64,head*32+ci*16+rc,64,kt*16);
   result[ci]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(b,a,result[ci]);
  }
  uint p=w2_pixel(win,qt*16+rc,workw),x=p%workw,y=p/workw;
  if(x>=sx&&y>=sy&&x<sx+width&&y<sy+height){
   uint dest=((y-sy)*width+x-sx)*64+head*32+gr*8;
   for(uint ci=0;ci<2;ci++){
    if constexpr(ByteOut){i2 a{};for(uint e=0;e<8;e++){float v=result[ci][e];w2_bits(a,e,q8_fused_round(post==0?Hrtz(v):v));}__builtin_memcpy(reinterpret_cast<unsigned char*>(out_any)+dest+ci*16,&a,8);}
    else for(uint e=0;e<8;e++){float v=result[ci][e];static_cast<float*>(out_any)[dest+ci*16+e]=post==3?Hrtz(v):post==0?F(Hrtz(v)):F(v);}
   }
  }
 }
}
#define W2_KERNEL(NAME,BI,BO) KERNEL __attribute__((amdgpu_flat_work_group_size(64,64))) void NAME(const float*in,const float*fw,const float*aw,void*out,uint w,uint h,uint ww,uint hh,uint sx,uint sy,uint post){c64_wave2_body<BI,BO>(in,fw,aw,out,w,h,ww,hh,sx,sy,post);}
W2_KERNEL(c64_wave2,false,false)
W2_KERNEL(c64_wave2_bi,true,false)
W2_KERNEL(c64_wave2_bo,false,true)
W2_KERNEL(c64_wave2_bi_bo,true,true)
