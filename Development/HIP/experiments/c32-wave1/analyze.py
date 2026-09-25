from pathlib import Path
import csv,json,statistics,sys
root=Path(sys.argv[1]);result={}
for p in sorted(root.glob('results-*/slots.csv')):
 rows=list(csv.DictReader(p.open()));pairs=[]
 for rep in sorted({int(r['repeat']) for r in rows}):
  group=sorted([r for r in rows if int(r['repeat'])==rep],key=lambda r:int(r['slot']))
  assert [int(r['mode']) for r in group]==[0,1,1,0]
  for r in group:
   assert int(r['target_calls'])==int(r['frames'])*4
   assert int(r['replaced'])==int(r['frames'])*4*int(r['mode'])
  t=[float(r['ms']) for r in group];pairs.append((t[1]+t[2]-t[0]-t[3])/2)
 result[p.parent.name]={'paired_delta_ms':pairs,'mean_delta_ms':statistics.mean(pairs)}
 print(p.parent.name,result[p.parent.name])
(root/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
