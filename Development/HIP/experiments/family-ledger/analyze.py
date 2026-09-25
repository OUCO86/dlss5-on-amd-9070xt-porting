# Region/family ledger from family-ledger CSVs (sparse prefix localABBA), with marker-perturbation controls.
from pathlib import Path
import csv,json,statistics,math,sys
root=Path(sys.argv[1]);repo=Path(__file__).resolve().parents[4]
labels=['input C32','encoder C32','encoder C64','encoder C128','encoder C256','encoder C512','bottleneck head','ViT','decoder transition','decoder C512','decoder C256','decoder C128','decoder C64','decoder C32','post/RGB']
family_regions={'C32':[0,1,13,14],'C64':[2,12],'C128':[3,11],'C256':[4,10],'C512':[5,9],'ViT':[7],'transitions':[6,8]}
old=json.loads((repo/'Development/results/network-timeline-20260921/summary.json').read_text())
res={}
for cfg in ('900-pdl1','1080-pdl1','900-pdl0','1080-pdl0'):
 d=root/cfg;tier=cfg.split('-')[0]
 b=[int(x) for x in (d/'bounds.txt').read_text().split()];rows=list(csv.DictReader((d/'prefix.csv').open()));base=list(csv.DictReader((d/'prefix-baseline.csv').open()))
 log=(d/'run.log').read_bytes();log=log.decode('utf-16') if log[:2]==b'\xff\xfe' else log.decode();assert log.count('bitdiff=0 invalid=0')==18 and 'PASS family ledger' in log
 rounds=len(rows)//60;assert len(rows)==60*rounds
 for r in rows:
  p,w,t,wall=map(float,[r['prefix_ms'],r['gpu_frame_ms'],r['tail_ms'],r['wall_ms']]);assert min(p,t)>=0 and w>0 and abs(p+t-w)<.00005 and w<=wall+.05
 regions=[]
 for i,l in enumerate(labels):
  pairs=[]
  for k in range(rounds):
   g=sorted([r for r in rows if int(r['region'])==i and int(r['round'])==k],key=lambda r:int(r['slot']));assert [int(r['cut']) for r in g]==[b[i],b[i+1],b[i+1],b[i]]
   v=[float(r['prefix_ms']) for r in g];pairs.append((v[1]+v[2]-v[0]-v[3])/2)
  regions.append(dict(region=l,start=b[i],end=b[i+1],dispatches=b[i+1]-b[i],mean_ms=statistics.mean(pairs),sd_ms=statistics.stdev(pairs)))
 total=sum(r['mean_ms'] for r in regions)
 fam={k:dict(mean_ms=sum(regions[i]['mean_ms'] for i in ids),dispatches=sum(regions[i]['dispatches'] for i in ids)) for k,ids in family_regions.items()}
 for v in fam.values():v['share_percent']=100*v['mean_ms']/total
 unmarked=statistics.median(float(r['wall_ms']) for r in base);marked=statistics.median(float(r['wall_ms']) for r in rows);span=statistics.median(float(r['gpu_frame_ms']) for r in rows)
 res[cfg]=dict(dispatches=b[-1],unmarked_wall_median_ms=unmarked,marked_wall_median_ms=marked,marker_perturbation_percent=100*(marked-unmarked)/unmarked,gpu_span_median_ms=span,reconstructed_ms=total,reconstruction_vs_span_percent=100*(total-span)/span,regions=regions,families=fam,old_families=old[tier]['families'])
(root/'summary.json').write_text(json.dumps(res,indent=2)+'\n')
for c,v in res.items():
 print(f"{c}: n={v['dispatches']} unmarked {v['unmarked_wall_median_ms']:.3f} marked {v['marked_wall_median_ms']:.3f} ({v['marker_perturbation_percent']:+.2f}%) span {v['gpu_span_median_ms']:.3f} sum {v['reconstructed_ms']:.3f} ({v['reconstruction_vs_span_percent']:+.2f}%)")
 print('   '+'  '.join(f"{k} {f['mean_ms']:.3f}({f['share_percent']:.1f}%) old {v['old_families'][k]['mean_ms']:.3f}" for k,f in v['families'].items()))
