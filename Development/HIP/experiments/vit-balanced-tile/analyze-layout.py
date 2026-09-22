from pathlib import Path
import csv,json,re,statistics,math,sys
root=Path(sys.argv[1]);result={};slots=0
for d in sorted(root.iterdir()):
 if not d.is_dir():continue
 net=(d/'network.csv').exists();p=d/('network.csv' if net else 'layout.csv')
 if not p.exists():continue
 rows=list(csv.DictReader(p.open()));assert len(rows)==(8 if net else 40);slots+=len(rows)
 for x in rows:
  assert int(x['bitdiff' if net else 'output_diff'])==0
  if net:assert int(x['replacements'])==(3200 if int(x['mode']) else 0)
  else:assert int(x['checked_bytes'])==int(x['tokens'])*(1024 if x['stage']=='pack' else 4096)
 assert 'PASS' in (d/'run.log').read_text()
 points=[]
 for line in (d/'telemetry.log').read_text().splitlines():
  q={k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',line)}
  if q.get('adapter')==0 and q.get('status')==0:points.append(q)
 def measure(xs):
  key='mean_ms' if net else 'mean_us';vals=[float(x[key]) for x in xs];assert all(math.isfinite(v) and v>0 for v in vals)
  picked=[q for q in points if any(int(x['start_ms'])<=q['tick']<=int(x['end_ms']) for x in xs)];tel={}
  for sensor in (1,2,73):
   v=[q[f'sensor{sensor}'] for q in picked if q.get(f'sensor{sensor}_supported')==1];tel[str(sensor)]={'n':len(v),'median':statistics.median(v),'min':min(v),'max':max(v)} if v else None
  return {'mean':statistics.mean(vals),'slots':vals,'telemetry':tel}
 stages=('network',) if net else ('shape_row','shape_tiled','layout_balanced','pack','pair');result[d.name]={}
 for stage in stages:
  rs=rows if net else [x for x in rows if x['stage']==stage];a=measure([x for x in rs if int(x['slot'])%4 in (0,3)]);b=measure([x for x in rs if int(x['slot'])%4 in (1,2)])
  result[d.name][stage]={'row':a,'tiled':b,'delta':b['mean']-a['mean'],'change_percent':100*(b['mean']/a['mean']-1)}
assert slots==96
(root/'layout-summary.json').write_text(json.dumps(result,indent=2)+'\n')
for name,stages in result.items():
 print(name)
 for stage,v in stages.items():
  med=lambda side,key:(v[side]['telemetry'][key] or {}).get('median')
  print(stage,round(v['row']['mean'],6),round(v['tiled']['mean'],6),round(v['change_percent'],3),'core',med('row','1'),med('tiled','1'),'mem',med('row','2'),med('tiled','2'))
