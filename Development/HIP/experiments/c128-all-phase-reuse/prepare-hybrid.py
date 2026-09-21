from pathlib import Path
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent
s=(here/'kernel.inc').read_text()
s=s.replace('const uint first=', 'const bool active=wave<8;\n const uint first=',1)
s=s.replace('i+=256','i+=512')
s=s.replace('f8 expand[2][4]','f8 expand[2][2]').replace('t<4','t<2').replace('wave*64+t*16','wave*32+t*16')
# Uniform barriers remain outside all active-half guards.
x=s.index(' f8 contract[2]');a=s[:x];t=s[x:]
t=t.replace('for(uint k=', 'if(active)for(uint k=')
# Normalize reduction belongs to the first128 threads, hence is already active.
t=t.replace('float ss=0;if(active)for(uint k=', 'float ss=0;for(uint k=')
t=t.replace('for(uint r=0;r<2;r++)for(uint e=0;e<8;e++)','if(active)for(uint r=0;r<2;r++)for(uint e=0;e<8;e++)')
t=t.replace('const float scale=w[9*C*C+wave*16+rc];','const float scale=active?w[9*C*C+wave*16+rc]:0.f;')
s=a+t
exports=[]
for mapped in (False,True):
 for bytein,fb in ((False,False),(False,True),(True,True)):
  name='mh_ffn_fused_c128_project_'+('mapped_' if mapped else '')+'g128_qkv'+('_bytein_fb' if bytein else '_fb' if fb else '')
  exports.append(f'KERNEL __attribute__((amdgpu_flat_work_group_size(512,512))) void {name}_m32(const float*in,const float*w,const float*aw,unsigned char*out,unsigned char*norm,uint tokens,uint width,uint height,uint workw,uint sx,uint sy){{mh_ffn_qkv_rows2<{str(mapped).lower()},{str(bytein).lower()},{str(fb).lower()}>(in,w,aw,out,norm,tokens,width,height,workw,sx,sy);}}')
out=Path('/tmp/c128-all-phase-reuse');out.mkdir(exist_ok=True)
(out/'hybrid.hip').write_text('#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_FFN_HOIST_RES 2\n'+(root/'hip/multihead_fast_padded.hip').read_text()+'\n'+s+'\n'+'\n'.join(exports)+'\n')
(here/'hybrid.inc').write_text(s)
