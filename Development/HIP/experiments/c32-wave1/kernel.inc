// One complete 64-token C32 window per wave; chain FP8 input/output.
#ifndef CW_LAUNDER
#define CW_LAUNDER 0
#endif
#ifndef CW_ROLL_HIDDEN
#define CW_ROLL_HIDDEN 0
#endif
using cw_i16=int __attribute__((ext_vector_type(16)));
DEV i2 cw_input(const unsigned char*in,uint win,uint qt,uint ci,uint width,uint height,uint sx,uint sy,uint prevw,uint px,uint py,uint r,uint g){
 uint ww=width+2*sx;int x=int((win%(ww/8))*8+(qt*16+r)%8)-int(sx),y=int((win/(ww/8))*8+(qt*16+r)/8)-int(sy);i2 a{};
 if(x>=0&&y>=0&&x<int(width)&&y<int(height)){uint xx=uint(x)+px,yy=uint(y)+py,tile=(yy/8)*(prevw/8)+xx/8,tok=(yy%8)*8+xx%8;__builtin_memcpy(&a,in+(tile*64+tok)*32+ci*16+g*8,8);}return a;
}
KERNEL __attribute__((amdgpu_flat_work_group_size(32,32)))
void c32_wave1_chain(const unsigned char*in,const float*fw,const float*w,unsigned char*out,uint windows,uint mode,uint raw,uint width,uint height,uint sx,uint sy,uint prevw,uint px,uint py){
 uint win=bid();if(win>=windows)return;
 __attribute__((shared)) _Float16 residual[4*2*32*8];
 i2 kv[2][4][2];cw_i16 queries{};
 _Pragma("unroll 4") for(uint qt=0;qt<4;qt++){
  uint lane=__builtin_amdgcn_workitem_id_x();
#if CW_LAUNDER
  __asm__ volatile("" : "+v"(lane));lane&=31u;
#endif
  uint r=lane&15u,g=lane>>4;
  i2 input[2];for(uint ci=0;ci<2;ci++)input[ci]=cw_input(in,win,qt,ci,width,height,sx,sy,prevw,px,py,r,g);
  f8 ffn[2]{};
  for(uint part=0;part<3;part++)for(uint ci=0;ci<2;ci++)for(uint kt=0;kt<2;kt++){
   i2 b=matrix8(fw,34944+((part*2+ci)*2+kt)*512+(g*16+r)*8);
   ffn[ci]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(b,input[kt],ffn[ci]);
  }
#if CW_ROLL_HIDDEN
  _Pragma("clang loop unroll(disable)")
#endif
  for(uint ht=0;ht<8;ht++){
   f8 expanded{};for(uint kt=0;kt<2;kt++){i2 b=matrix8(fw+512,(ht*16+r)*32+kt*16+g*8);expanded=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(b,input[kt],expanded);}
   i2 a{};for(uint e=0;e<8;e++){float v=expanded[e],g=clampf(v,-4.f,4.f),q=absf(g)*(-.055908203125f)+.447265625f,p=g*q+.89453125f;put_bits(a,e,fp8(v*p));}
   for(uint ci=0;ci<2;ci++){i2 b=matrix8(fw+4608,(ci*16+r)*128+ht*16+g*8);ffn[ci]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(b,a,ffn[ci]);}
  }
  i2 feature[2];for(uint ci=0;ci<2;ci++){i2 a{};for(uint e=0;e<8;e++){float v=Hrtz(ffn[ci][e]);residual[((qt*2+ci)*32+(g*16+r))*8+e]=(_Float16)v;put_bits(a,e,fp8(v));}feature[ci]=a;}
  for(uint part=0;part<3;part++){
   f8 q[2]{};for(uint ci=0;ci<2;ci++)for(uint kt=0;kt<2;kt++){i2 b=matrix8(w,part*1024+(ci*16+r)*32+kt*16+g*8);q[ci]=part<2?__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(b,feature[kt],q[ci]):__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(feature[kt],b,q[ci]);}
   f8 sum{};if(part<2)for(uint ci=0;ci<2;ci++){h8 squares{},ones{};for(uint e=0;e<8;e++){squares[e]=(_Float16)(q[ci][e]*q[ci][e]);ones[e]=(_Float16)1.f;}sum=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(ones,squares,sum);}
   for(uint ci=0;ci<2;ci++){i2 a{};for(uint e=0;e<8;e++){float v=q[ci][e];if(part<2)v*=__builtin_amdgcn_rsqf(maxf(sum[e],6.198883056640625e-5f))*(part==0?w[8192]:1.f);put_bits(a,e,fp8(v));}
    if(part==0){queries[qt*4+ci*2]=a[0];queries[qt*4+ci*2+1]=a[1];}else kv[part-1][qt][ci]=a;
   }
  }
  __builtin_amdgcn_sched_barrier(0);
 }
 _Pragma("clang loop unroll(disable)") for(uint qt=0;qt<4;qt++){
  uint lane=__builtin_amdgcn_workitem_id_x();
#if CW_LAUNDER
  __asm__ volatile("" : "+v"(lane));lane&=31u;
#endif
  uint r=lane&15u,g=lane>>4;
  i2 q[2];for(uint ci=0;ci<2;ci++)q[ci]=i2{queries[qt*4+ci*2],queries[qt*4+ci*2+1]};
  h8 ex[4];
  _Pragma("unroll 4") for(uint kt=0;kt<4;kt++){
   f8 acc{};for(uint ci=0;ci<2;ci++)acc=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(kv[0][kt][ci],q[ci],acc);
   h8 a{};for(uint e=0;e<8;e++){uint row=qt*16+r,k=kt*16+g*8+e;float score=acc[e]+w[4096+row*64+k],affine=clampf(score*.044921875f+1.30078125f,1.03125f,1.5693359375f);uint ah=(bits(affine)>>13)-0x1c000u;ushort hb=static_cast<ushort>(((ah<<5)+0x8000u)&65535u);a[e]=__builtin_bit_cast(_Float16,hb);}ex[kt]=a;
  }
  f8 sums{};h8 ones{};for(uint e=0;e<8;e++)ones[e]=(_Float16)1.f;
  _Pragma("unroll 4") for(uint kt=0;kt<4;kt++)sums=__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12(ones,ex[kt],sums);
  i2 prob[4];_Pragma("unroll 4") for(uint kt=0;kt<4;kt++){i2 a{};for(uint e=0;e<8;e++)put_bits(a,e,fp8(float(ex[kt][e])*norm_inverse(sums[e])));prob[kt]=a;}
  i2 av[2];for(uint ci=0;ci<2;ci++){f8 acc{};_Pragma("unroll 4") for(uint kt=0;kt<4;kt++)acc=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(kv[1][kt][ci],prob[kt],acc);i2 a{};for(uint e=0;e<8;e++)put_bits(a,e,fp8(acc[e]));av[ci]=a;}
  for(uint ci=0;ci<2;ci++){
   f8 acc{};for(uint kt=0;kt<2;kt++){i2 b=matrix8(w,3072+(ci*16+r)*32+kt*16+g*8);acc=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(b,av[kt],acc);}
   i2 a{};for(uint e=0;e<8;e++){float res=float(residual[((qt*2+ci)*32+(g*16+r))*8+e]),prod=res*w[8193+ci*16+g*8+e],v=Hrtz(acc[e]+prod);put_bits(a,e,fp8(F(float((_Float16)v))));}
   __builtin_memcpy(out+(win*64+qt*16+r)*32+ci*16+g*8,&a,8);
  }
  __builtin_amdgcn_sched_barrier(0);
 }
}
