from pathlib import Path
import subprocess,shutil,json,re
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent;out=Path('/tmp/network-fixed-shapes');out.mkdir(exist_ok=True)
def source(name):return subprocess.check_output(['git','show','2f4c8fa:hip/'+name+'.hip'],cwd=root,text=True)
def function(s,name):
 a=s.index('void '+name+'(');b=s.index('{',a);level=1;e=b+1
 while level:
  level+=(s[e]=='{')-(s[e]=='}');e+=1
 return s[a:b],s[b:e]
def clone(s,name,attr,cases):
 sig,body=function(s,name);params=sig[sig.index('(')+1:sig.rindex(')')];args=[re.search(r'(\w+)\s*$',x)[1] for x in params.split(',')]
 helper=name+'_fixed_body';code='\nDEV '+sig.replace(name,helper,1)+body+'\n'
 branches=[]
 for condition,replacements in cases:
  call=','.join(replacements.get(x,x) for x in args);branches.append('if('+condition+')'+helper+'('+call+');')
 branches.append(helper+'('+','.join(args)+');')
 code+=attr+' '+sig.replace(name,'probe_'+name,1)+'{'+'else '.join(branches)+'}\n'
 return code
s=source('deep_fast');code=s
name='vit_expand_blocked_fp8_frag_bytein';sig,body=function(s,name)
code+='\nWAVE '+sig.replace(name,'probe_'+name,1)+'{if(reuse_gate&&reuse_gate[0])return;if(inputs==1024&&outputs==4096)vit_expand_blocked_body<true,true,true>(in,w,out,tokens,1024,4096);else vit_expand_blocked_body<true,true,true>(in,w,out,tokens,inputs,outputs);}\n'
code+=clone(s,'vit_project_frag','WAVE',[('inputs==1024&&outputs==1024',{'inputs':'1024','outputs':'1024'})])
for n in ('decoder_project2x_h16w','decoder_project2x_h16w_byteout'):
 code+=clone(s,n,'WAVE',[(f'inputs=={c}&&outputs=={c//2}',{'inputs':str(c),'outputs':str(c//2)}) for c in (1024,512,256,128,64)])
for cap in (256,400,640):
 name=f'vit_attention_fused_{cap}_bytein';sig,body=function(s,name)
 code+='\nWAVE '+sig.replace(name,'probe_'+name,1)+f'{{if(reuse_gate&&reuse_gate[0])return;if(tokens=={cap})vit_attention_fused_body<{cap},true>(in,out,{cap});else vit_attention_fused_body<{cap},true>(in,out,tokens);}}\n'
code+=clone(s,'vit_qkv_project_normalize_fused_f16compact_fp8_frag','WAVE',[(f'tokens=={n}',{'tokens':str(n)}) for n in (256,400,640)])
(out/'deep.hip').write_text('#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_BRANCHLESS_F 1\n'+code)
s=source('multihead_fast_padded');s+=clone(s,'mh_pool_project_production_h16w','FASTWAVE',[('channels==32',{'channels':'32'})]);(out/'mh.hip').write_text('#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_FFN_HOIST_RES 2\n'+s)
s=source('multihead_fused_attention');s+=clone(s,'mh_attention_fused_fp8_out','KERNEL __attribute__((amdgpu_flat_work_group_size(128,128)))',[('channels==512',{'channels':'512'})]);(out/'attention.hip').write_text('#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_MH_RTZ_ISA 1\n'+s)
s=source('multihead_reference')
for n in ('mh_shift_pack','mh_pool'):s+=clone(s,n,'KERNEL',[('channels==512',{'channels':'512'})])
(out/'reference.hip').write_text('#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n'+s)
(out/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (root/'Development/HIP').glob('*.h'):shutil.copyfile(p,out/'Development/HIP'/p.name)
p=out/'Development/HIP/hip_reference_network.h';s=p.read_text().replace('class Network {','class Network {\n unsigned schedule_mode=0;unsigned schedule_replaced=0;',1)
needle='for(unsigned repeat=0;repeat<repeats_here;repeat++)api.Check('
insert='''bool selected=((schedule_mode&1)&&kernel=="vit_expand_blocked_fp8_frag_bytein")||((schedule_mode&2)&&kernel=="vit_project_frag")||((schedule_mode&4)&&(kernel=="decoder_project2x_h16w"||kernel=="decoder_project2x_h16w_byteout"))||((schedule_mode&8)&&kernel=="mh_pool_project_production_h16w")||((schedule_mode&16)&&kernel=="mh_attention_fused_fp8_out")||((schedule_mode&32)&&(kernel=="mh_shift_pack"||kernel=="mh_pool"));selected=selected||((schedule_mode&64)&&kernel.rfind("vit_attention_fused_",0)==0&&kernel.find("_bytein")!=std::string::npos)||((schedule_mode&128)&&kernel=="vit_qkv_project_normalize_fused_f16compact_fp8_frag");if(selected){kernel="probe_"+kernel;schedule_replaced++;}'''
assert s.count(needle)==1;s=s.replace(needle,insert+needle,1).replace(' Handle Stream()const{return stream;}',' void SetSchedule(unsigned n){schedule_mode=n;schedule_replaced=0;}\n unsigned ScheduleReplaced()const{return schedule_replaced;}\n Handle Stream()const{return stream;}',1);p.write_text(s)
x=(root/'src/native_hip_network.h').read_text();a=x.index('hip_reference::Options o;');b=x.index('  const wchar_t*modules=',a)
opts=x[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift','o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)','o.assets=argv[1]')
s=(root/'Development/HIP/experiments/vit-schedule-cause/runner.cpp.in').read_text();a=s.index(' for(unsigned frame=0;');b=s.index('api.hipFree(x);',a);s=s[:a]+(here/'timing.inc').read_text()+s[b:];(out/'network.cpp').write_text(s.replace('/* OPTIONS */',opts).replace('PASS ViT schedule controls','PASS fixed shape controls'))
