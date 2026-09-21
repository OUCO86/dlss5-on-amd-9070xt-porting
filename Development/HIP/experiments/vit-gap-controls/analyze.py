from pathlib import Path
import csv,json,re,statistics,sys,math
root=Path(sys.argv[1]);results={};total=0
for d in sorted(root.iterdir()):
 if not d.is_dir() or not (d/'schedule.csv').exists():continue
 rows=list(csv.DictReader((d/'schedule.csv').open()));assert len(rows)==(80 if re.fullmatch(r'(900|1080)-expand',d.name) else 8)
 assert all(int(x['output_diff'])==0 and int(x['checked_bytes'])==int(x['tokens'])*4096 and math.isfinite(float(x['mean_us'])) and float(x['mean_us'])>0 for x in rows)
 assert (d/'run.log').read_text().count('bitdiff=0')==2;total+=len(rows)
 samples=[]
 for line in (d/'telemetry.log').read_text().splitlines():
  p={k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',line)}
  if p.get('adapter')==0 and p.get('status')==0:samples.append(p)
 def stats(rs):
  p=[x for x in samples if any(int(y['start_ms'])<=x['tick']<=int(y['end_ms']) for y in rs)];values=[float(x['mean_us']) for x in rs];us=statistics.mean(values);tokens=int(rs[0]['tokens']);tf=2*tokens*1024*4096/us/1e6
  telemetry={}
  for key in (1,2,73):
   v=[x[f'sensor{key}'] for x in p if x.get(f'sensor{key}_supported')==1];telemetry[str(key)]={'n':len(v),'median':statistics.median(v),'min':min(v),'max':max(v)} if v else None
  clock=telemetry['1']['median'] if telemetry['1'] else None;peak=64*2048*clock/1e6 if clock else None
  return {'us':us,'slots_us':values,'range_percent':100*(max(values)-min(values))/us,'principal_tflops':tf,'telemetry':telemetry,'clock_reference_tf':peak,'reference_fraction':tf/peak if peak else None}
 results[d.name]={}
 for name in sorted(set(x['variant'] for x in rows)):
  xs=[x for x in rows if x['variant']==name];a=stats([x for x in xs if int(x['slot'])%4 in (0,3)]);b=stats([x for x in xs if int(x['slot'])%4 in (1,2)])
  results[d.name][name]={'baseline':a,'candidate':b,'change_percent':100*(b['us']/a['us']-1)}
assert total==192,total
(root/'summary.json').write_text(json.dumps(results,indent=2)+'\n')
for case,rs in results.items():
 print(case)
 for name,v in rs.items():
  a=v['baseline'];b=v['candidate'];print(name,round(a['us'],3),round(b['us'],3),'core',a['telemetry']['1']['median'],b['telemetry']['1']['median'],'mem',a['telemetry']['2']['median'],b['telemetry']['2']['median'])
print('checked slots',total,'raw checks',len(results)*2)
