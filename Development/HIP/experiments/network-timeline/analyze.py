from pathlib import Path
import csv,json,statistics,math,re,sys
root=Path(sys.argv[1]);repo=Path(__file__).resolve().parents[4]
labels=['input C32','encoder C32','encoder C64','encoder C128','encoder C256','encoder C512','bottleneck head','ViT','decoder transition','decoder C512','decoder C256','decoder C128','decoder C64','decoder C32','post/RGB']
bounds=[0,1,5,14,27,44,101,103,152,154,189,206,219,228,233,234]
family_regions={'C32':[0,1,13,14],'C64':[2,12],'C128':[3,11],'C256':[4,10],'C512':[5,9],'ViT':[7],'transitions':[6,8]}
old=json.loads((repo/'Development/results/9070-theoretical-20260921/estimate.json').read_text());result={}
for tier in ('900','1080'):
 d=root/tier
 rows=list(csv.DictReader((d/'prefix.csv').open()));base=list(csv.DictReader((d/'prefix-baseline.csv').open()));dense=list(csv.DictReader((d/'frames.csv').open()));top=list(csv.DictReader((d/'timeline.csv').open()))
 assert len(rows)==480 and len(base)==200 and len(top)==16*234
 assert (d/'prefix.log').read_text().count('bitdiff=0 invalid=0')==17
 for r in rows:
  p,w,t,wall=map(float,[r['prefix_ms'],r['gpu_frame_ms'],r['tail_ms'],r['wall_ms']]);assert all(math.isfinite(v) for v in (p,w,t,wall)) and min(p,t)>=0 and w>0 and abs(p+t-w)<.00005 and w<=wall+.05
 regions=[]
 for i,label in enumerate(labels):
  pairs=[]
  for repetition in range(8):
   group=sorted([r for r in rows if int(r['region'])==i and int(r['round'])==repetition],key=lambda r:int(r['slot']));assert len(group)==4
   assert [int(r['cut']) for r in group]==[bounds[i],bounds[i+1],bounds[i+1],bounds[i]]
   v=[float(r['prefix_ms']) for r in group];pairs.append((v[1]+v[2]-v[0]-v[3])/2)
  regions.append(dict(region=label,start=bounds[i],end=bounds[i+1],dispatches=bounds[i+1]-bounds[i],mean_ms=statistics.mean(pairs),paired_min_ms=min(pairs),paired_max_ms=max(pairs),pairs_ms=pairs))
 total=sum(r['mean_ms'] for r in regions)
 families={name:dict(mean_ms=sum(regions[i]['mean_ms'] for i in ids),dispatches=sum(regions[i]['dispatches'] for i in ids)) for name,ids in family_regions.items()}
 # Prior analytic principal matrices are intentionally approximate, not all ISA FLOPs.
 gf=old[tier]['stages_GFLOP'];model={'C32':gf['C32/fp8']+gf['input-head/fp16']+gf['RGB/fp32'],'C64':gf['C64/fp8'],'C128':gf['C128/fp8'],'C256':gf['C256/fp8'],'C512':gf['C512/fp8']+gf['C512/fp16'],'ViT':gf['ViT/fp8']+gf['ViT/fp16']+gf['ViT-attention/fp8']}
 saved={'C128':0.,'C256':0.}
 for r in [r for r in top if r['frame']=='0']:
  m=re.match(r'mh_ffn_fused_c(128|256).*_mapped_.*qkv',r['kernel'])
  if not m:continue
  c=int(m[1]);a=r['scalar_args'].split(';');n=int(a[5]);height=int(a[7]);workw=int(a[8]);sy=int(a[10]);empty=sum(first+15<sy*workw or first>=(sy+height)*workw for first in range(0,n,16))*16
  saved[f'C{c}']+=2*empty*(8*c*c+128*c)/1e9
 for k,v in saved.items():model[k]-=v
 for k,v in families.items():
  v['compute_share_percent']=100*v['mean_ms']/total
  if k in model:v['approx_principal_GFLOP']=model[k];v['approx_principal_TFLOPS']=model[k]/v['mean_ms']
 normal=statistics.median(float(r['wall_ms']) for r in base);profile=statistics.median(float(r['wall_ms']) for r in rows);span=statistics.median(float(r['gpu_frame_ms']) for r in rows)
 result[tier]=dict(normal_wall_median_ms=normal,prefix_wall_median_ms=profile,prefix_gpu_span_median_ms=span,reconstructed_compute_ms=total,reconstruction_vs_span_percent=100*(total-span)/span,dense_normal_wall_median_ms=statistics.median(float(r['wall_ms']) for r in dense if int(r['phase'])%2==0),dense_traced_wall_median_ms=statistics.median(float(r['wall_ms']) for r in dense if int(r['phase'])%2==1),regions=regions,families=families,zero_guard_principal_GFLOP_removed=saved,raw_output_checks=17)
(root/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
for tier,d in result.items():
 print(tier,'normal/profile/span/sum',*[round(d[k],4) for k in ('normal_wall_median_ms','prefix_wall_median_ms','prefix_gpu_span_median_ms','reconstructed_compute_ms')])
 for k,v in d['families'].items():print(k,round(v['mean_ms'],4),round(v['compute_share_percent'],2),'GF',round(v.get('approx_principal_GFLOP',0),2),'effective TF',round(v.get('approx_principal_TFLOPS',0),2))
