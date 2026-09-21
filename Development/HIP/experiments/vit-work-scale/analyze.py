from pathlib import Path
import csv,json,re,statistics,sys,math
root=Path(sys.argv[1]);all_results={};slots=0;checks=0
for d in sorted(root.iterdir()):
 if not d.is_dir():continue
 streams=(d/'streams.csv').exists();file=d/('streams.csv' if streams else 'scale.csv')
 if not file.exists():continue
 rows=list(csv.DictReader(file.open()));assert len(rows)==(32 if streams else 128)
 assert (d/'run.log').read_text().count('bitdiff=0')==2;checks+=2;slots+=len(rows)
 points=[]
 for line in (d/'telemetry.log').read_text().splitlines():
  p={k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',line)}
  if p.get('adapter')==0 and p.get('status')==0:points.append(p)
 for x in rows:
  n=int(x['tokens']);bm=int(x['bm']);copies=int(x['copies']);base=not streams and x['original']=='1';active=1 if base else copies
  assert int(x['output_diff'])==0 and int(x['checked_bytes'])==n*4096*active
  assert int(x['groups'])==(n*4 if base else ((n+16*bm-1)//(16*bm))*64*copies)
  assert math.isfinite(float(x['mean_us'])) and float(x['mean_us'])>0 and abs(float(x['mean_us'])/active-float(x['per_copy_us']))<1e-6
 def stat(rs):
  us=statistics.mean(float(x['per_copy_us']) for x in rs);n=int(rs[0]['tokens']);tf=2*n*1024*4096/us/1e6
  selected=[p for p in points if any(int(x['start_ms'])<=p['tick']<=int(x['end_ms']) for x in rs)];sensors={}
  for i in (1,2,73):
   v=[p[f'sensor{i}'] for p in selected if p.get(f'sensor{i}_supported')==1];sensors[str(i)]={'samples':len(v),'median':statistics.median(v),'min':min(v),'max':max(v)} if v else None
  ref=64*2048*sensors['1']['median']/1e6 if sensors['1'] else None
  return {'per_copy_us':us,'slot_us':[float(x['per_copy_us']) for x in rs],'principal_tflops':tf,'clock_reference_tf':ref,'telemetry':sensors}
 results={}
 for bm in (1,2):
  for order in ('major','interleave'):
   for copies in ((8,) if streams else (1,2,4,8)):
    xs=[x for x in rows if int(x['bm'])==bm and x['order']==order and int(x['copies'])==copies];assert len(xs)==8
    a=stat([x for x in xs if int(x['slot'])%4 in (0,3)]);b=stat([x for x in xs if int(x['slot'])%4 in (1,2)]);results[f'm{bm}-{order}-r{copies}']={'baseline':a,'candidate':b,'change_percent':100*(b['per_copy_us']/a['per_copy_us']-1)}
 all_results[d.name]=results
assert slots==288 and checks==6,(slots,checks)
(root/'summary.json').write_text(json.dumps(all_results,indent=2)+'\n')
for case,rs in all_results.items():
 print(case)
 for name,x in rs.items():
  a=x['baseline'];b=x['candidate'];print(name,round(a['per_copy_us'],3),round(b['per_copy_us'],3),'TF',round(b['principal_tflops'],1),'core',b['telemetry']['1']['median'] if b['telemetry']['1'] else None,'mem',b['telemetry']['2']['median'] if b['telemetry']['2'] else None)
print('validated',slots,'slots',checks,'raw checks')
