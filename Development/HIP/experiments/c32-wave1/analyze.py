from pathlib import Path
import csv,json,statistics,sys
root=Path(sys.argv[1]);result={}
for p in sorted(root.glob('results-*/slots.csv')):
 rows=list(csv.DictReader(p.open()));variants={}
 for candidate in sorted({int(r['candidate']) for r in rows}):
  pairs=[]
  for rep in sorted({int(r['repeat']) for r in rows}):
   group=sorted([r for r in rows if int(r['repeat'])==rep and int(r['candidate'])==candidate],key=lambda r:int(r['slot']))
   assert [int(r['mode']) for r in group]==[0,candidate,candidate,0]
   for r in group:
    assert int(r['target_calls']) in ((int(r['frames'])*4,int(r['frames'])*8) if candidate==1 else (int(r['frames'])*8,))
    assert int(r['replaced'])==int(r['frames'])*[0,4,2,2,8][int(r['mode'])]
   t=[float(r['ms']) for r in group];pairs.append((t[1]+t[2]-t[0]-t[3])/2)
  variants[str(candidate)]={'paired_delta_ms':pairs,'mean_delta_ms':statistics.mean(pairs)}
 result[p.parent.name]=variants;print(p.parent.name,variants)
(root/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
