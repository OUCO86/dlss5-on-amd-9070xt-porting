from pathlib import Path
import difflib,subprocess
root=Path(__file__).resolve().parents[4];old=subprocess.check_output(['git','show','e151f8b:hip/c32_fused_ffn_attention.hip'],cwd=root,text=True);a=old.index('  for(uint task=l;task<48;task+=32)');b=old.index('\n }\n}',a)
new='''  if(l<16){uint tok=first+l;int x=int((window%(ww/8))*8+tok%8)-int(sx),y=int((window/(ww/8))*8+tok/8)-int(sy);
   if(x>=0&&y>=0&&x<int(sourcew)&&y<int(sourceh)){uint p=uint(y)*sourcew+uint(x);float a0=0.f,a1=0.f,a2=0.f;
    for(uint j=0;j<32;j++){float f=float(scratch.ex[tok*34+j]);a0+=f*headw[j];a1+=f*headw[32+j];a2+=f*headw[64+j];}
    float sums[3]={a0,a1,a2};for(uint row=0;row<3;row++){float acc=Hrtz(sums[row]),centered=color[p*4+row]*.125f-.0625f,v=(acc*rgb_scale+centered)*8.f+.5f;rgb[p*3+row]=clampf(v,0.f,1.f);}
   }
  }'''
s=old[:a]+new+old[b:];out=Path('/tmp/post-head-shared-input');out.mkdir(exist_ok=True);(out/'c32_fused_ffn_attention.hip').write_text(s)
(root/'Development/HIP/experiments/post-head-shared-input/candidate.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='a/hip/c32_fused_ffn_attention.hip',tofile='b/hip/c32_fused_ffn_attention.hip')))
