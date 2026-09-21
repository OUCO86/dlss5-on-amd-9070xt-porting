"""Summarize the small evidence archive exported by collect.ps1."""
from pathlib import Path
import csv,json,statistics,sys,re
root=Path(sys.argv[1]);hashes=json.loads((root/'hashes.json').read_text(encoding='utf-8-sig'))
h={(r['tag'],r['file']):r['sha'] for r in hashes}
controls=[]
for base,candidate in [(f'base-{height}-{seq}',f'candidate-{height}-{seq}') for height in (900,1080) for seq in (0,1)]+[(f'extra-{case}-False',f'extra-{case}-True') for case in ('720-motion','900-history','900-float-in','900-float-feature')]:
 for frame in range(12):
  f=f'rgb-frame-{frame}.f16';a=h.get((base,f));b=h.get((candidate,f));assert a and b and a==b,(base,candidate,frame,a,b)
 controls.append({'base':base,'candidate':candidate,'matching_frames':12})
result={'controls':controls,'timing':{}}
for prefix in ('time','repeat'):
 for height in (900,1080):
  times=[]
  for slot in range(4):
   p=root/f'{prefix}-{height}-{slot}'/'rgb.csv'
   if not p.exists():break
   rows=list(csv.DictReader(p.open(encoding='utf-8-sig')));cut=200 if len(rows)>=1000 else 32
   assert all(not r['invalid'] or int(r['invalid'])==0 for r in rows)
   times.append(statistics.mean(float(r['wall_ms']) for r in rows[cut:]))
  if len(times)==4:
   base=(times[0]+times[3])/2;test=(times[1]+times[2])/2
   result['timing'][f'{prefix}-{height}']={'slots_ms':times,'base_ms':base,'candidate_ms':test,'saved_ms':base-test,'saved_percent':100*(base-test)/base}
kernel=[]
for slot in range(4):
 text=(root/f'kernel-{slot}.log').read_text(encoding='utf-8-sig')
 values=re.findall(r'PURE frame=\d+ bitdiff=(\d+)',text);assert values==['0','0'],(slot,values)
 kernel.append(float(re.search(r'mean_us=([0-9.]+)',text)[1]))
baseline=(kernel[0]+kernel[3])/2;candidate=(kernel[1]+kernel[2])/2
result['isolated_fused_kernel']={'slots_us':kernel,'base_us':baseline,'candidate_us':candidate,'saved_percent':100*(baseline-candidate)/baseline,'raw_fp32_comparisons':8,'bitdiff':0}
(root/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
