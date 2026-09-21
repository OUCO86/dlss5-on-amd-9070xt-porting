from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent
out=Path('/tmp/c128-all-phase-reuse');out.mkdir(exist_ok=True)
shutil.copytree(root/'src',out/'src',dirs_exist_ok=True);(out/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (root/'Development/HIP').glob('*.h'):shutil.copyfile(p,out/'Development/HIP'/p.name)
shutil.copyfile(root/'Development/HIP/benchmark_vit_reuse.cpp',out/'Development/HIP/benchmark.cpp')
s=(root/'hip/multihead_fast_padded.hip').read_text()
body=(here/'kernel.inc').read_text()
exports=[];names=[]
for mapped in (False,True):
 for bytein,fb in ((False,False),(False,True),(True,True)):
  name='mh_ffn_fused_c128_project_'+('mapped_' if mapped else '')+'g128_qkv'+('_bytein_fb' if bytein else '_fb' if fb else '')
  names.append(name)
  exports.append(f'KERNEL __attribute__((amdgpu_flat_work_group_size(256,256))) void {name}_m32(const float*in,const float*w,const float*aw,unsigned char*out,unsigned char*norm,uint tokens,uint width,uint height,uint workw,uint sx,uint sy){{mh_ffn_qkv_rows2<{str(mapped).lower()},{str(bytein).lower()},{str(fb).lower()}>(in,w,aw,out,norm,tokens,width,height,workw,sx,sy);}}')
(out/'multihead_fast_padded.hip').write_text('#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_FFN_HOIST_RES 2\n'+s+'\n'+body+'\n'+'\n'.join(exports)+'\n')

p=out/'Development/HIP/hip_reference_network.h';s=p.read_text();needle='  if(module=="mh_fast"){';assert s.count(needle)==1
# Route only known compatible entries, preserve all alternative modes.
s=s.replace(needle,needle+'\n   static const std::set<std::string> m32={'+','.join('"'+n+'"' for n in names)+'};\n   if(m32.count(kernel)&&!std::getenv("DLSS5_C128_M32_DISABLE")){if(count%(128*32))throw std::runtime_error("C128 M32 shape");kernel+="_m32";}')
needle='threads=c*2;groups=count/(c*16);';assert s.count(needle)==1
s=s.replace(needle,needle+'if(kernel.size()>4&&kernel.compare(kernel.size()-4,4,"_m32")==0){threads=256;groups=count/(c*32);}')
p.write_text(s)
print(out)
