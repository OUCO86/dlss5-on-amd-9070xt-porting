// C512 attention + projection, one wave owns one 32-channel head of an 8x8 window (16 waves, 512 threads).
// Replaces mh_attention_fused_fp8_out (one head per 4-wave group, AV bytes to global) followed by
// mh_attention_project_frag_c512 (crop) / mh_attention_project_fast_scalar_fp8 (identity).
// Inputs are the production ones: normalized FP8 [pixel][Q,K,V][512] from mh_qkv_normalize_frag_c512, the f32 FFN
// feature, and PackedMhWeightQkvFrag weights (projection E4M3 fragment tiles at float offset 3*C*C; score bias and
// residual scales keep their float offsets). AV bytes stay in LDS. The projection keeps production's operand
// orientation (A = AV rows, B = weight fragment), K order 0..511, Hrtz(feature*scale) accumulator start and the
// post 0/3/4 epilogue, so every output element is the same dot product in the same order.
// The attention core (scores, exp, WMMA row sums, probabilities, AV) is spliced from wave_owned_mh.inc by prepare.py.
// QS waves share one head: each owns 4/QS query tiles; K/V of all 64 tokens come from the shared V staging.
template<uint QS>
DEV void c512_attn_wave_body(const unsigned char*normalized,const float*aw,const float*feature,float*out,
 uint workw,uint workh,uint cropw,uint croph,uint sx,uint sy,uint post){
 constexpr uint C=512,QN=4/QS;
 const uint win=__builtin_amdgcn_workgroup_id_x(),tid=__builtin_amdgcn_workitem_id_x(),head=(tid/32)%16,q0=(tid/32/16)*QN;
 const uint rc=w2_rc(),gr=w2_gr();
 if(win>=(workw/8)*(workh/8))return;
 __attribute__((shared)) unsigned char plane1[64*C];
 // Stage this head's V in A-fragment layout; each wave then reads it transposed into B fragments.
 for(uint qt=q0;qt<q0+QN;qt++)for(uint ci=0;ci<2;ci++){
  uint p=w2_pixel(win,qt*16+rc,workw),col=head*32+ci*16+gr*8;i2 v;
  __builtin_memcpy(&v,normalized+(p*3+2)*C+col,8);w2_store<C>(plane1,qt,head*2+ci,v);
 }
 w2_sync();
 i2 qkv[3][4][2];
#if W2_ROLL_QUERY
 w2_i16 query_words{};
#endif
 _Pragma("unroll 4") for(uint qt=0;qt<4;qt++){
  _Pragma("unroll 2") for(uint ci=0;ci<2;ci++){
   uint p=w2_pixel(win,qt*16+rc,workw),col=head*32+ci*16+gr*8;i2 q,k,v{};
   __builtin_memcpy(&q,normalized+p*3*C+col,8);__builtin_memcpy(&k,normalized+(p*3+1)*C+col,8);
   for(uint e=0;e<8;e++){
    uint token=gr*8+e,channel=ci*16+rc;
    uint lane=token+(channel%16/8)*16,ct=head*2+channel/16;
    w2_bits(v,e,plane1[((qt*(C/16)+ct)*32+lane)*8+channel%8]);
   }
#if W2_ROLL_QUERY
   query_words[qt*4+ci*2]=q[0];query_words[qt*4+ci*2+1]=q[1];
#else
   qkv[0][qt][ci]=q;
#endif
   qkv[1][qt][ci]=k;qkv[2][qt][ci]=v;
  }
  w2_schedule();
 }
 w2_sync(); // Every head has consumed V before the plane becomes AV output.
/*ATTENTION_CORE*/
 w2_sync();
 // Projection: all four query tiles of this head's 32 output channels; weights read once per K step.
 const unsigned char*wb=reinterpret_cast<const unsigned char*>(aw)+size_t(3)*C*C*4;const uint skip=4*C*C+(C/32)*4096+C/32;
 f8 acc[QN][2];
 _Pragma("unroll") for(uint n=0;n<2;n++){uint c=head*32+n*16+rc;float scale=aw[skip+c];
  _Pragma("unroll") for(uint qi=0;qi<QN;qi++)for(uint e=0;e<8;e++){uint p=w2_pixel(win,(q0+qi)*16+gr*8+e,workw);acc[qi][n][e]=Hrtz(feature[p*C+c]*scale);}}
#if C5_ROLL_K
 _Pragma("clang loop unroll(disable)")
#endif
 for(uint kt=0;kt<C/16;kt++){
  uint gs=kt/2,h=kt%2;i2 b[2];
  _Pragma("unroll") for(uint n=0;n<2;n++){uint n0=head*32+n*16+rc;__builtin_memcpy(&b[n],wb+((n0/16)*16+gs)*512+((h*2+gr)*16+n0%16)*8,8);}
  _Pragma("unroll") for(uint qi=0;qi<QN;qi++){i2 a=w2_load<C>(plane1,q0+qi,kt);
   _Pragma("unroll") for(uint n=0;n<2;n++)acc[qi][n]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b[n],acc[qi][n]);}
 }
 _Pragma("unroll") for(uint qi=0;qi<QN;qi++)_Pragma("unroll") for(uint n=0;n<2;n++)for(uint e=0;e<8;e++){
  uint p=w2_pixel(win,(q0+qi)*16+gr*8+e,workw),c=head*32+n*16+rc;float a=acc[qi][n][e],v=post==3?Hrtz(a):post==4?F(a):F(Hrtz(a));uint dest=p*C+c;
  if(cropw){uint x=p%workw,y=p/workw;if(x<sx||y<sy||x>=sx+cropw||y>=sy+croph)continue;dest=((y-sy)*cropw+x-sx)*C+c;}
  out[dest]=v;
 }
}
#define C5_KERNEL(NAME,QS) KERNEL __attribute__((amdgpu_flat_work_group_size(512*QS,512*QS))) void NAME(const unsigned char*n,const float*w,const float*f,float*o,uint ww,uint hh,uint cw,uint ch,uint sx,uint sy,uint post){c512_attn_wave_body<QS>(n,w,f,o,ww,hh,cw,ch,sx,sy,post);}
C5_KERNEL(c512_attn_wave,1)
C5_KERNEL(c512_attn_wave2,2)
