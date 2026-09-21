from pathlib import Path
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent
s=(here/'kernel.inc').read_text()
a=s.index(' union Storage');b=s.index(' if constexpr(!ByteIn)',a)
s=s[:a]+''' // One 16KiB arena: expansion -> contracted input -> feature+normalization scratch.
 __attribute__((shared)) unsigned char arena[16384];
 auto*hidden=arena;auto*feature=arena;
 auto*raw=reinterpret_cast<float*>(arena+32*132);
 auto*inverse=reinterpret_cast<float*>(arena+32*132+16*4*33*4);
 auto hindex=[](uint row,uint col)->uint{return row*512+(col^((row&15)*8));};
'''+s[b:]
s=s.replace('hidden[(r*16+g*8+e)*516+wave*64+t*16+rc]','hidden[hindex(r*16+g*8+e,wave*64+t*16+rc)]')
s=s.replace('hidden+(r*16+rc)*516+k+g*8','hidden+hindex(r*16+rc,k+g*8)')
needle=' for(uint r=0;r<2;r++)for(uint e=0;e<8;e++){uint row=r*16+g*8+e,byte='
assert s.count(needle)==1
s=s.replace(needle,' // Every projection read completes before its input arena becomes feature output.\n __builtin_amdgcn_s_barrier();\n'+needle)
a=s.index('  if(part<2){')
s=s[:a]+'''  // Normalize one row tile at a time. This halves scratch, preserving the original 32-term sum.
  for(uint r=0;r<2;r++){
   if(part<2){
    for(uint e=0;e<8;e++)raw[((wave/2)*16+g*8+e)*33+(wave%2)*16+rc]=q[r][e];
    __builtin_amdgcn_s_barrier();
    if(tid<64){uint head=tid/16,row=tid%16;float ss=0;for(uint k=0;k<32;k++){float v=raw[(head*16+row)*33+k];ss+=v*v;}inverse[tid]=__builtin_amdgcn_rsqf(maxf(ss,6.198883056640625e-5f))*(part==0?aw[4*C*C+4*4096+head]:1.f);}
    __builtin_amdgcn_s_barrier();
   }
   for(uint e=0;e<8;e++){uint row=g*8+e;float inv=part<2?inverse[(wave/2)*16+row]:1.f;norm[((first+r*16+row)*3+part)*C+wave*16+rc]=static_cast<unsigned char>(q8_fused_round(q[r][e]*inv));}
  }
 }
}
'''
exports=[]
for mapped in (False,True):
 for bytein,fb in ((False,False),(False,True),(True,True)):
  name='mh_ffn_fused_c128_project_'+('mapped_' if mapped else '')+'g128_qkv'+('_bytein_fb' if bytein else '_fb' if fb else '')
  exports.append(f'KERNEL __attribute__((amdgpu_flat_work_group_size(256,256))) void {name}_m32(const float*in,const float*w,const float*aw,unsigned char*out,unsigned char*norm,uint tokens,uint width,uint height,uint workw,uint sx,uint sy){{mh_ffn_qkv_rows2<{str(mapped).lower()},{str(bytein).lower()},{str(fb).lower()}>(in,w,aw,out,norm,tokens,width,height,workw,sx,sy);}}')
out=Path('/tmp/c128-all-phase-reuse');out.mkdir(exist_ok=True)
(out/'compact.hip').write_text('#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_FFN_HOIST_RES 2\n'+(root/'hip/multihead_fast_padded.hip').read_text()+'\n'+s+'\n'+'\n'.join(exports)+'\n')
(here/'compact.inc').write_text(s)
