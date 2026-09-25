from pathlib import Path
import csv,json,re,statistics,sys
root=Path(sys.argv[1]);hashes={c['tag']:c for c in json.loads((root/'frame-hashes.json').read_text())}
pairs=[(f'base-{h}-{seq}',f'candidate-{h}-{seq}') for h in [900,1080] for seq in [0,1]]+[(f'extra-{case}-False',f'extra-{case}-True') for case in ['720-motion','900-history']]
summary={'correctness':[],'timing':{}}
def inspect(tag,enabled):
 rows=list(csv.DictReader((root/tag/'rgb.csv').open()));log=(root/tag/'run.log').read_text()
 assert rows and all(int(r['invalid'])==0 for r in rows if int(r['checked']))
 counters=re.findall(r'WAVE_OWNED_RUNTIME calls=(\d+) replaced=(\d+) enabled=(\d+)',log)
 assert counters,tag
 for calls,replaced,mode in counters:
  assert int(calls)>=46*len(rows) and int(calls)%46==0
  assert int(mode)==enabled and int(replaced)==(int(calls) if enabled else 0)
 return rows
for base,candidate in pairs:
 for tag,enabled in [(base,0),(candidate,1)]:assert len(inspect(tag,enabled))==12 and hashes[tag]['count']==12
 a=hashes[base]['frames'];b=hashes[candidate]['frames'];assert len(a)==len(b)==12 and a==b,(base,candidate)
 assert hashes[base]['final_sha256']==hashes[candidate]['final_sha256']
 summary['correctness'].append({'baseline':base,'candidate':candidate,'matching_frames':12})
summary['candidate_frames_bit_exact']=sum(x['matching_frames'] for x in summary['correctness'])
for height in [900,1080]:
 times=[]
 for slot in range(4):
  tag=f'repeat-{height}-{slot}';rows=inspect(tag,int(slot in [1,2]));assert len(rows)==1000
  times.append(statistics.mean(float(r['wall_ms']) for r in rows if int(r['frame'])>=200))
 base=(times[0]+times[3])/2;candidate=(times[1]+times[2])/2
 summary['timing'][str(height)]={'slots_ms':times,'baseline_ms':base,'candidate_ms':candidate,'delta_ms':candidate-base,'time_reduction_percent':100*(base-candidate)/base,'frames_per_slot':1000,'warmup_excluded':200}
(root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
