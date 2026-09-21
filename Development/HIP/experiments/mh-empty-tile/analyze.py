from pathlib import Path
import re,json,csv,statistics,sys
root=Path(sys.argv[1]);result={'controls':[],'timing':{},'kernels':{}}
hashes=json.loads((root/'hashes.json').read_text(encoding='utf-8-sig'));h={(x['tag'],x['file']):x['sha'] for x in hashes}
if '--kernel-only' not in sys.argv:
 pairs=[(f'base-{height}-{seq}',f'candidate-{height}-{seq}') for height in (900,1080) for seq in (0,1)]
 if '--basic-only' not in sys.argv:pairs += [(f'extra-{case}-False',f'extra-{case}-True') for case in ('720-motion','900-history','900-float-in','900-float-feature')]
 for base,candidate in pairs:
  for frame in range(12):
   fn=f'rgb-frame-{frame}.f16';assert h.get((base,fn)) and h[(base,fn)]==h.get((candidate,fn)),(base,frame)
  result['controls'].append({'base':base,'candidate':candidate,'matching_frames':12})
for prefix in ('time','repeat'):
 for height in (900,1080):
  values=[]
  for slot in range(4):
   p=root/f'{prefix}-{height}-{slot}'/'rgb.csv'
   if not p.exists():break
   rows=list(csv.DictReader(p.open(encoding='utf-8-sig')));cut=200 if len(rows)>=1000 else 32
   assert all(not r['invalid'] or int(r['invalid'])==0 for r in rows)
   values.append(statistics.mean(float(r['wall_ms']) for r in rows[cut:]))
  if len(values)==4:
   base=(values[0]+values[3])/2;candidate=(values[1]+values[2])/2
   result['timing'][f'{prefix}-{height}']={'slots_ms':values,'base_ms':base,'candidate_ms':candidate,'saved_ms':base-candidate}
for target in ('c64','c256'):
 if not(root/f'kernel-{target}-0.log').exists():continue
 values=[]
 for slot in range(4):
  t=(root/f'kernel-{target}-{slot}.log').read_text(encoding='utf-8-sig')
  assert re.findall(r'PURE frame=\d+ bitdiff=(\d+)',t)==['0','0']
  values.append(float(re.search(r'EMPTY_TILE .* us=([\d.]+)',t)[1]))
 base=(values[0]+values[3])/2;candidate=(values[1]+values[2])/2
 result['kernels'][target]={'slots_us':values,'base_us':base,'candidate_us':candidate,'saved_percent':100*(base-candidate)/base,'raw_fp32_comparisons':8,'bitdiff':0}
(root/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
