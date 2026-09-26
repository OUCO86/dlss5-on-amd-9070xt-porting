from pathlib import Path
import csv,json,statistics,sys,re
root=Path(sys.argv[1]);result={}
for p in sorted(root.glob('results-*/slots.csv')):
 rows=list(csv.DictReader(p.open()));out={}
 for candidate in sorted({int(r['candidate']) for r in rows}):
  pairs=[];bases=[]
  for rep in sorted({int(r['repeat']) for r in rows}):
   group=sorted([r for r in rows if int(r['repeat'])==rep and int(r['candidate'])==candidate],key=lambda r:int(r['slot']))
   assert [int(r['mode']) for r in group]==[0,candidate,candidate,0]
   for r in group:
    assert int(r['target_calls'])==int(r['frames'])*46
    assert int(r['replaced'])==int(r['frames'])*[0,36,10,46][int(r['mode'])]
   t=[float(r['ms']) for r in group];bases.append((t[0]+t[3])/2);pairs.append((t[1]+t[2]-t[0]-t[3])/2)
  out[str(candidate)]={'paired_delta_ms':pairs,'mean_delta_ms':statistics.mean(pairs),'baseline_ms':statistics.mean(bases),'time_reduction_percent':-100*statistics.mean(pairs)/statistics.mean(bases)}
 log=(p.parent/'run.log').read_text();assert 'PASS combined wave ownership' in log
 checks=re.findall(r'VERIFY bitdiff=(\d+) invalid=(\d+)',log);assert checks and all(a=='0' and b=='0' for a,b in checks)
 dyn=re.findall(r'DYNAMIC frame=(\d+) candidate=(\d+) seed=(\d+) history=(\d+) calls=(\d+) replaced=(\d+)\nVERIFY bitdiff=0 invalid=0',log)
 for frame,candidate,seed,history,calls,replaced in dyn:
  assert int(seed)==123+int(frame)*17 and int(history)==int(int(frame)>0)
  assert int(calls)==46 and int(replaced)==[0,36,10,46][int(candidate)]

 for candidate in sorted({int(r['candidate']) for r in rows}):
  assert [int(d[0]) for d in dyn if int(d[1])==candidate]==list(range(16))
 out['dynamic_frames_verified']=len(dyn);result[p.parent.name]=out;print(p.parent.name,out)
(root/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
