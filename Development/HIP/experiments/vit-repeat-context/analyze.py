from pathlib import Path
import csv,json,re,statistics,math,sys
root=Path(sys.argv[1]);out={}
for d in sorted(root.iterdir()):
 if not (d/'repeat.csv').exists() or d.name.startswith('pilot-'):continue
 rows=list(csv.DictReader((d/'repeat.csv').open()));assert len(rows)==(40 if d.name in ("1080","900") else 24)
 for x in rows:
  f,r,m=int(x['frames']),int(x['repeats']),int(x['mode']);assert x['bitdiff']=='0' and int(x['pairs'])==f*8 and int(x['extra_pairs'])==f*8*(r-1) and int(x['expand_launches'])==f*8*r and int(x['replacements'])==f*16*m
  assert math.isfinite(float(x['wall_ms'])) and float(x['wall_ms'])>0
 points=[]
 for line in (d/'telemetry.log').read_text().splitlines():
  p={k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',line)}
  if p.get('adapter')==0 and p.get('status')==0:points.append(p)
 def measure(rs):
  ps=[p for p in points if any(int(x['start_ms'])<=p['tick']<=int(x['end_ms']) for x in rs)];tel={}
  for sensor in (1,2,73):
   vals=[p[f'sensor{sensor}'] for p in ps if p.get(f'sensor{sensor}_supported')==1];tel[str(sensor)]={'median':statistics.median(vals),'min':min(vals),'max':max(vals),'n':len(vals)} if vals else None
  return {'mean_ms':statistics.mean(float(x['wall_ms']) for x in rs),'slots_ms':[float(x['wall_ms']) for x in rs],'telemetry':tel}
 out[d.name]={}
 for test in dict.fromkeys(x['test'] for x in rows):
  rs=[x for x in rows if x['test']==test];a=measure([x for x in rs if int(x['slot'])%4 in (0,3)]);b=measure([x for x in rs if int(x['slot'])%4 in (1,2)]);delta=b['mean_ms']-a['mean_ms']
  out[d.name][test]={'A':a,'B':b,'delta_ms':delta,'change_percent':100*delta/a['mean_ms']}
  if test.startswith('slope'):out[d.name][test]['marginal_us_per_extra_pair']=delta*1000/24
(root/'summary.json').write_text(json.dumps(out,indent=2)+'\n')
for case,tests in out.items():
 print(case)
 for test,v in tests.items():print(test,round(v['A']['mean_ms'],6),round(v['B']['mean_ms'],6),'delta',round(v['delta_ms'],6),'core',v['A']['telemetry']['1']['median'],v['B']['telemetry']['1']['median'],'mem',v['A']['telemetry']['2']['median'],v['B']['telemetry']['2']['median'])
