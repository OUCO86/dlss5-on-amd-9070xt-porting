from pathlib import Path
import csv,json,statistics,math,sys
root=Path(sys.argv[1]);out={}
for d in sorted(root.iterdir()):
 if not d.is_dir():continue
 if d.name.startswith('prefix-'):
  r=list(csv.DictReader((d/'prefix.csv').open()));c=list(csv.DictReader((d/'control.csv').open()));assert len(r)==512 and len(c)==16
  assert all(x['valid']=='1' for x in r) and all(x['bitdiff']=='0' for x in c)
  out[d.name]={}
  for mode in (0,1):
   rows=[x for x in r if int(x['mode'])==mode];groups={}
   for x in rows:groups.setdefault((x['slot'],x['round']),[]).append(x)
   ds=[1000*(statistics.mean(float(x['prefix_ms']) for x in g if x['after']=='1')-statistics.mean(float(x['prefix_ms']) for x in g if x['after']=='0')) for g in groups.values()]
   plain=statistics.mean(float(x['wall_ms']) for x in c if int(x['mode'])==mode);marked=statistics.mean(float(x['wall_ms']) for x in rows)
   slot_deltas={slot:statistics.mean(1000*(statistics.mean(float(x['prefix_ms']) for x in g if x['after']=='1')-statistics.mean(float(x['prefix_ms']) for x in g if x['after']=='0')) for (sl,_),g in groups.items() if sl==slot) for slot in sorted(set(x['slot'] for x in rows))}
   out[d.name][mode]={'prefix_delta_us':statistics.mean(ds),'round_std_us':statistics.stdev(ds),'min_delta_us':min(ds),'max_delta_us':max(ds),'slot_deltas_us':slot_deltas,'plain_wall_ms':plain,'marked_wall_ms':marked,'marker_wall_change_percent':100*(marked/plain-1)}
 elif d.name.startswith('region-'):
  r=list(csv.DictReader((d/'context.csv').open()));e=list(csv.DictReader((d/'events.csv').open()));assert len(r)==32 and len(e)==2560
  assert all(x['bitdiff']=='0' and int(x['replacements'])==(2560 if int(x['mode']) else 0) for x in r)
  assert all(math.isfinite(float(x['segment_ms'])) and float(x['segment_ms'])>0 for x in e)
  out[d.name]={}
  for test in dict.fromkeys(x['test'] for x in r):
   group=[x for x in r if x['test']==test];sides=[]
   for bb in [False,True]:
    xs=[x for x in group if (int(x['slot'])%4 in (1,2))==bb]
    sides.append({'wall_ms':statistics.mean(float(x['wall_ms']) for x in xs),'wall_slots':[float(x['wall_ms']) for x in xs],'segment_ms':statistics.mean(float(x['segment_ms']) for x in xs)})
   out[d.name][test]={'A':sides[0],'B':sides[1],'wall_change_percent':100*(sides[1]['wall_ms']/sides[0]['wall_ms']-1)}
 else:
  p=d/'events.csv'
  if p.exists():
   r=list(csv.DictReader(p.open()));v=[float(x['segment_ms']) for x in r]
   if v:out[d.name]={'rejected_samples':len(v),'nonpositive':sum(x<=0 for x in v),'min_ms':min(v),'max_ms':max(v),'mean_ms':statistics.mean(v)}
(root/'summary.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
