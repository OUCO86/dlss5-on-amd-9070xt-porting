from pathlib import Path
import csv,json,statistics,sys,math
r=Path(sys.argv[1]);counts={1:8,2:8,4:5,8:2,16:13,32:14,64:8,128:8}
def count(mode):return sum(v for k,v in counts.items() if mode&k)
summary={}
for d in sorted(r.iterdir()):
 if not d.is_dir() or not (d/'network.csv').exists():continue
 rows=list(csv.DictReader((d/'network.csv').open()));assert len(rows)==(32 if d.name.startswith('network-') else 4)
 assert all(int(x['bitdiff'])==0 and int(x['replacements'])==count(int(x['mode']))*int(x['frames']) for x in rows)
 summary[d.name]={}
 for v in sorted(set(x['variant'] for x in rows),key=int):
  xs=[x for x in rows if x['variant']==v];a=statistics.mean(float(x['mean_ms']) for x in xs if int(x['slot']) in (0,3));b=statistics.mean(float(x['mean_ms']) for x in xs if int(x['slot']) in (1,2));summary[d.name][v]={'baseline_ms':a,'candidate_ms':b,'delta_ms':b-a}
(r/'sweep-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
if not (r/'regression').exists():raise SystemExit('Sweep only; regression missing')
reg={}
for d in sorted((r/'regression').iterdir()):
 rows=list(csv.DictReader((d/'rgb.csv').open()));assert len(rows) in (12,1000);assert all(math.isfinite(float(x['wall_ms'])) for x in rows);assert all(int(x['invalid'])==0 for x in rows if x['checked']=='1');assert rows[0]['checked']==rows[-1]['checked']=='1'
 if len(rows)==12:assert all(x['checked']=='1' for x in rows)
 if len(rows)==1000:reg[d.name]=statistics.mean(float(x['wall_ms']) for x in rows if int(x['frame'])>=200)
assert len(reg)==8
result={}
for h in (900,1080):
 base=statistics.mean(reg[f'time-{h}-{i}'] for i in (0,3));test=statistics.mean(reg[f'time-{h}-{i}'] for i in (1,2));result[str(h)]={'baseline_ms':base,'candidate_ms':test,'saved_ms':base-test,'saved_percent':100*(base-test)/base}
hashes=json.loads((r/'rgb-hashes.json').read_text());by={(x['case'],x['file']):x for x in hashes};pairs=0
for x in hashes:
 case=x['case']
 if case.startswith('base-'):other='candidate-'+case[5:]
 elif case.endswith('-False'):other=case[:-6]+'-True'
 else:continue
 y=by[(other,x['file'])];assert x['sha']==y['sha'] and x['bytes']==y['bytes']
 if 'frame-' in x['file']:pairs+=1
assert pairs==96,pairs
result['rgb_frame_pairs']=pairs;result['timing_frames']=8000
(r/'regression-summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
