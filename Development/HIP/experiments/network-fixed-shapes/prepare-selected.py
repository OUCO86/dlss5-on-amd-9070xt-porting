from pathlib import Path
import runpy,sys
here=Path(__file__).resolve().parent
x=runpy.run_path(str(here/'prepare.py'));s=x['source']('deep_fast');function=x['function'];clone=x['clone'];out=x['out']
name='vit_expand_blocked_fp8_frag_bytein';sig,body=function(s,name)
replacement='WAVE '+sig+'{if(reuse_gate&&reuse_gate[0])return;if(inputs==1024&&outputs==4096)vit_expand_blocked_body<true,true,true>(in,w,out,tokens,1024,4096);else vit_expand_blocked_body<true,true,true>(in,w,out,tokens,inputs,outputs);}'
s=s.replace('WAVE '+sig+body,'// Fixed model dimensions expose the K-loop schedule; retain the generic ABI fallback.\n'+replacement,1)
for name in ['vit_project_frag']+(['decoder_project2x_h16w','decoder_project2x_h16w_byteout'] if '--decoder' in sys.argv else []):
 cases=[('inputs==1024&&outputs==1024',{'inputs':'1024','outputs':'1024'})] if name=='vit_project_frag' else [(f'inputs=={c}&&outputs=={c//2}',{'inputs':str(c),'outputs':str(c//2)}) for c in (1024,512,256,128,64)]
 sig,body=function(s,name);new=clone(s,name,'WAVE',cases).replace('probe_'+name,name)
 s=s.replace('WAVE '+sig+body,new.strip(),1)
(out/'selected-source.hip').write_text(s)
(out/'selected-packed.hip').write_text('#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_BRANCHLESS_F 1\n'+s)
(out/'selected-unpacked.hip').write_text('#define HIP_ISA_HALF 1\n'+s)
