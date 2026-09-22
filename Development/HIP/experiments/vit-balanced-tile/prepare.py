from pathlib import Path
import subprocess,shutil
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent;out=Path('/tmp/vit-balanced-tile');out.mkdir(exist_ok=True)
s=subprocess.check_output(['git','show','cdfd6b6:hip/deep_fast.hip'],cwd=root,text=True)
code='#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_BRANCHLESS_F 1\n'+s+'\n'
code+='WAVE void probe_control(const float*in,const float*w,float*out,uint tokens,uint inputs,uint outputs,const uint*gate){if(gate&&gate[0])return;vit_expand_blocked_body<true,true,true>(in,w,out,tokens,1024,4096);}\n'
for name,unroll,colmajor in [('m32n32_u4',4,False),('m32n32_u1',1,False),('m32n32_col',4,True)]:
 body=r'''
template<uint BM>
DEV void BODY(const float*in,const float*w,float*out,uint first,uint col){
 f8 accum[BM][2]{};
 #pragma unroll UNROLL
 for(uint k=0;k<1024;k+=16){
  i2 a[BM],b[2];
  #pragma unroll
  for(uint m=0;m<BM;m++){
   const uint*p=reinterpret_cast<const uint*>(in);uint off=((first+m*16+rc())*1024+k+gr()*8)/4;
   a[m]={int(p[off]),int(p[off+1])};
  }
  #pragma unroll
  for(uint n=0;n<2;n++)b[n]=vit_weight_fragment_native(w,col+n*16+rc(),1024,k);
  #pragma unroll
  for(uint m=0;m<BM;m++){
   #pragma unroll
   for(uint n=0;n<2;n++)accum[m][n]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a[m],b[n],accum[m][n]);
  }
 }
 #pragma unroll
 for(uint m=0;m<BM;m++){
  #pragma unroll
  for(uint n=0;n<2;n++)for(uint e=0;e<8;e++){
   float v=accum[m][n][e],g=clampf(v,-4.f,4.f),poly=__builtin_fmaf(g,absf(g)*(-.055908203125f)+.447265625f,.89453125f);
   reinterpret_cast<unsigned char*>(out)[(first+m*16+gr()*8+e)*4096+col+n*16+rc()]=byte_F(v*poly);
  }
 }
}
WAVE void EXPORT(const float*in,const float*w,float*out,uint tokens,uint inputs,uint outputs,const uint*gate){
 if(gate&&gate[0])return;
 INDEX
 if(first>=tokens)return;
 if(first+16<tokens)BODY<2>(in,w,out,first,col);else BODY<1>(in,w,out,first,col);
}
'''
 index='uint mt=(tokens+31)/32,first=(bid()%mt)*32,col=(bid()/mt)*32;' if colmajor else 'uint first=(bid()/128)*32,col=(bid()%128)*32;'
 code+=body.replace('BODY','balanced_'+name).replace('EXPORT','probe_'+name).replace('UNROLL',str(unroll)).replace('INDEX',index)
(out/'kernel.hip').write_text(code)
(out/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (root/'Development/HIP').glob('*.h'):shutil.copyfile(p,out/'Development/HIP'/p.name)
p=out/'Development/HIP/hip_reference_network.h';s=p.read_text().replace('class Network {','class Network {\n bool c32_probe_done=false;',1)
needle='for(unsigned repeat=0;repeat<repeats_here;repeat++)api.Check(';assert s.count(needle)==1
s=s.replace(needle,(here/'timing.inc').read_text()+needle,1).replace(' Handle Stream()const{return stream;}',' bool C32ProbeDone()const{return c32_probe_done;}\n Handle Stream()const{return stream;}',1);p.write_text(s)
x=(root/'src/native_hip_network.h').read_text();a=x.index('hip_reference::Options o;');b=x.index('  const wchar_t*modules=',a)
opts=x[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift','o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)','o.assets=argv[1]')
runner=(here.parent/'vit-compute-density/runner.cpp.in').read_text().replace('/* OPTIONS */',opts).replace('PASS ViT density controls','PASS ViT balanced tile')
(out/'pure.cpp').write_text(runner)
print(out)
