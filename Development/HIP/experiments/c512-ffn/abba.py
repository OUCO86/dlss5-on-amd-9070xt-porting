import csv,sys,collections
for f in sys.argv[1:]:
  rows=list(csv.DictReader(open(f)));d=collections.defaultdict(list)
  for r in rows:d[(r['repeat'],r['candidate'])].append((int(r['mode']),float(r['ms'])))
  out=collections.defaultdict(list);base=[]
  for k,v in d.items():
    b=[m for mo,m in v if mo==0];x=[m for mo,m in v if mo!=0];out[k[1]].append(sum(x)/len(x)-sum(b)/len(b));base+=b
  bm=sum(base)/len(base)
  for c,v in out.items():print(f.split('/')[-1],'cand',c,'base %.4f'%bm,'diffs',' '.join('%+.4f'%x for x in v),'mean %+.4f ms (%+.2f%%)'%(sum(v)/len(v),100*sum(v)/len(v)/bm))
