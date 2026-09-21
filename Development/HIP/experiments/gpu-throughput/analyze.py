from pathlib import Path
import csv,json,re,statistics,sys
root=Path(sys.argv[1]);records=[]
nominal={'fp8':389.,'fp16':195.,'fp32':48.7,'fp32d':48.7}
per_cu={'fp8':2048,'fp16':1024,'fp32':256,'fp32d':256}
for folder in sorted(p for p in root.iterdir() if p.is_dir() and (p/'timing.csv').exists()):
 log=(folder/'run.log').read_text(encoding='utf-8-sig');assert 'FAIL' not in log and 'PASS configurations=' in log
 rows=list(csv.DictReader((folder/'timing.csv').open(encoding='utf-8-sig')))
 samples=[]
 for line in (folder/'telemetry.log').read_text(encoding='utf-8-sig').splitlines():
  d=dict(re.findall(r'(\w+)=(-?\d+)',line))
  if d.get('adapter')=='0' and d.get('status')=='0':samples.append({k:int(v) for k,v in d.items()})
 cases={}
 for row in rows:
  kind=row['kind'];acc=int(row['accumulators']);groups=int(row['groups']);it=int(row['iterations']);launches=int(row['launches'])
  expected=groups*(256*2 if kind.startswith('fp32') else 8*8192)*acc*16*it
  assert float(row['flops_per_launch'])==expected
  for timer in ('wall','event'):
   ms=float(row[timer+'_ms']);tf=float(row[timer+'_tflops']);assert ms>0 and abs(tf-expected*launches/(ms*1e9))<1e-6
  cases.setdefault((kind,acc,groups),[]).append(row)
 for (kind,acc,groups),rs in cases.items():
  start=min(int(r['start_tick']) for r in rs);end=max(int(r['end_tick']) for r in rs)
  telemetry=[x for x in samples if start<=x['tick']<=end]
  sensors={}
  for sensor,name in ((1,'core_MHz'),(2,'memory_clock_report_MHz'),(8,'edge_C'),(27,'hotspot_C'),(73,'board_W')):
   v=[x[f'sensor{sensor}'] for x in telemetry if x.get(f'sensor{sensor}_supported')]
   sensors[name]=dict(samples=len(v),min=min(v),median=statistics.median(v),max=max(v)) if v else None
  wall=[float(r['wall_tflops']) for r in rs];event=[float(r['event_tflops']) for r in rs]
  tf=statistics.median(wall);clock=sensors['core_MHz'];peak=64*per_cu[kind]*clock['median']/1e6 if clock else None
  records.append(dict(run=folder.name,kind=kind,accumulators=acc,groups=groups,samples=len(rs),wall_tflops=dict(min=min(wall),median=tf,max=max(wall)),event_tflops_median=statistics.median(event),nominal_tflops=nominal[kind],nominal_percent=tf/nominal[kind]*100,clock_adjusted_reference=peak,clock_adjusted_percent=tf/peak*100 if peak else None,telemetry=sensors,max_wall_event_difference_percent=max(abs(float(r['wall_ms'])-float(r['event_ms']))/float(r['wall_ms'])*100 for r in rs)))
best={k:max((r for r in records if r['kind']==k),key=lambda r:r['wall_tflops']['median']) for k in nominal}
(root/'summary.json').write_text(json.dumps({'configurations':records,'best':best},indent=2)+'\n')
for r in records:
 if r['run'].startswith('repeat-'):
  print(r['kind'],r['wall_tflops'],'core',r['telemetry']['core_MHz'],'power',r['telemetry']['board_W'],'clock_adjusted_percent',r['clock_adjusted_percent'])
print('Validated configurations:',len(records))
