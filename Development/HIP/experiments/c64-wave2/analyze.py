"""Validate ABBA membership/call counts and summarize each independent prototype run."""
from pathlib import Path
import csv,json,statistics,sys
from collections import defaultdict
root=Path(sys.argv[1]);result={}
for path in sorted(root.glob('results-*/slots.csv')):
 groups=defaultdict(list)
 for row in csv.DictReader(path.open()):groups[int(row['repeat']),int(row.get('candidate',1))].append(row)
 stats=defaultdict(list)
 for (rep,candidate),rows in sorted(groups.items()):
  rows.sort(key=lambda x:int(x['slot']))
  assert [int(r['mode']) for r in rows]==[0,candidate,candidate,0],path
  for r in rows:
   frames=int(r['frames'])
   if 'target_calls' in r:
    assert int(r['target_calls'])==frames*36
    assert int(r['replaced'])==frames*[0,8,12,16,36,20][int(r['mode'])]
   else:assert int(r['c64_calls'])==frames*8
  times=[float(r['ms']) for r in rows];delta=(times[1]+times[2]-times[0]-times[3])/2
  stats[candidate].append(delta)
 result[path.parent.name]={str(k):{'paired_delta_ms':v,'mean_delta_ms':statistics.mean(v)} for k,v in stats.items()}
 for k,v in stats.items():print(path.parent.name,'mode',k,'B-A ms',','.join(f'{x:+.5f}' for x in v),'mean',f'{statistics.mean(v):+.5f}')
(root/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
