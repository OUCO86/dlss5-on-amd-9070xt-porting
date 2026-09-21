from pathlib import Path
import csv,json,re,statistics,math,sys
root=Path(sys.argv[1]);result={};slots=0
for d in sorted(root.iterdir()):
 if not d.is_dir() or not (d/'schedule.csv').exists():continue
 rows=list(csv.DictReader((d/'schedule.csv').open()));assert len(rows)==56;slots+=len(rows)
 assert all(int(x['output_diff'])==0 and int(x['checked_bytes'])==int(x['tokens'])*4096 and math.isfinite(float(x['mean_us'])) and float(x['mean_us'])>0 for x in rows)
 assert (d/'run.log').read_text().count('bitdiff=0')==2
 points=[]
 for line in (d/'telemetry.log').read_text().splitlines():
  p={k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',line)}
  if p.get('adapter')==0 and p.get('status')==0:points.append(p)
 def measure(xs,factor):
  us=statistics.mean(float(x['mean_us']) for x in xs);t=int(xs[0]['tokens']);tf=2*t*1024*4096*factor/us/1e6
  ps=[p for p in points if any(int(x['start_ms'])<=p['tick']<=int(x['end_ms']) for x in xs)];sensors={}
  for k in (1,2,73):
   vals=[p[f'sensor{k}'] for p in ps if p.get(f'sensor{k}_supported')==1];sensors[str(k)]={'n':len(vals),'median':statistics.median(vals),'min':min(vals),'max':max(vals)} if vals else None
  ref=64*2048*sensors['1']['median']/1e6 if sensors['1'] else None
  return {'mean_us':us,'slots_us':[float(x['mean_us']) for x in xs],'matrix_instruction_work_factor':factor,'executed_matrix_tflops':tf,'clock_reference_tf':ref,'reference_ratio':tf/ref if ref else None,'telemetry':sensors}
 result[d.name]={}
 for name in ('work1','work2','work4','work8','control2','control4','control8'):
  xs=[x for x in rows if x['variant']==name];assert len(xs)==8;factor=int(name[4:]) if name.startswith('work') else 1
  a=measure([x for x in xs if int(x['slot'])%4 in (0,3)],1);b=measure([x for x in xs if int(x['slot'])%4 in (1,2)],factor)
  result[d.name][name]={'baseline':a,'candidate':b,'time_change_percent':100*(b['mean_us']/a['mean_us']-1)}
assert slots==336,slots
(root/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
for case,variants in result.items():
 if case.startswith('uniform'):
  print(case)
  for name,v in variants.items():
   q=v['candidate'];print(name,round(v['baseline']['mean_us'],3),round(q['mean_us'],3),'TF',round(q['executed_matrix_tflops'],2),'core',(q['telemetry']['1'] or {}).get('median'),'mem',(q['telemetry']['2'] or {}).get('median'),'ref%',round(100*q['reference_ratio'],2) if q['reference_ratio'] else None)
print('validated slots',slots,'raw checks',len(result)*2)
