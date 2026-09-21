from pathlib import Path
import shutil,subprocess
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent;out=Path('/tmp/c128-norm-cost');out.mkdir(exist_ok=True)
shutil.copytree(root/'src',out/'src',dirs_exist_ok=True);(out/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (root/'Development/HIP').glob('*.h'):shutil.copyfile(p,out/'Development/HIP'/p.name)
s=subprocess.check_output(['git','show','79c1654:hip/multihead_fast_padded.hip'],cwd=root,text=True);a=s.index('template<uint C,bool Tiled=false,bool Project=false,bool Mapped=false,bool Grouped=false,bool ByteIn=false,bool ByteFeature=false,bool BatchNorm=false,bool Frag=false>\nDEV void mh_ffn_qkv_body');b=s.index('\nKERNEL ',a)
body=s[a:b].replace('mh_ffn_qkv_body','mh_ffn_qkv_norm_cost',1).replace('unsigned char*norm=nullptr){','unsigned char*norm=nullptr,uint mode=0,uint repeats=1){',1)
body=body.replace('static_assert(Project&&Grouped,','static_assert(C==128&&ByteIn&&ByteFeature&&!Tiled&&!Frag&&!BatchNorm&&Project&&Grouped,',1)
a=body.index('   if(part<2){for(uint e=0;e<8;e++)storage.raw[');b=body.index('\n   for(uint e=0;e<8;e++){uint row=group*8+e;',a)
body=body[:a]+'''   if(part<2){
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
'''+body[b:]
export='''KERNEL __attribute__((amdgpu_flat_work_group_size(256,256))) void c128_norm_cost(const float*in,const float*w,const float*aw,unsigned char*out,unsigned char*norm,uint tokens,uint width,uint height,uint workw,uint sx,uint sy,uint mode,uint repeats){mh_ffn_qkv_norm_cost<128,false,true,true,true,true,true>(in,w,out,tokens,width,height,workw,sx,sy,aw,norm,mode,repeats);}
'''
(out/'kernel.hip').write_text('#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_FFN_HOIST_RES 2\n'+s+'\n'+body+'\n'+export)
(here/'kernel.inc').write_text(body+'\n'+export)
# Reuse the validated real-input pure HIP harness, post_shift=3.
helper=root/'Development/HIP/experiments/kernel-bottleneck/prepare-pure.py'
x=helper.read_text().replace("out=Path('/tmp/kernel-bottleneck')", "out=Path('/tmp/c128-norm-cost')")
exec(compile(x,str(helper),'exec'),{'__file__':str(helper)})
p=out/'Development/HIP/hip_reference_network.h';s=p.read_text().replace('class Network {','class Network {\n bool norm_cost_done=false;',1)
needle='for(unsigned repeat=0;repeat<repeats_here;repeat++)api.Check('
assert s.count(needle)==1
injection=(here/'timing.inc').read_text()
s=s.replace(needle,injection+needle,1);p.write_text(s)
print(out)
