from pathlib import Path
import csv,json,re,statistics,math,collections,sys
root=Path(sys.argv[1]);summary={}
for d in sorted(root.iterdir()):
 if not d.is_dir() or not (d/'timing.csv').exists():continue
 for p in d.iterdir():
  if p.is_file():
   raw=p.read_bytes();s=raw.decode('utf-16') if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else raw.decode('utf-8-sig')
   p.write_text('\n'.join(x.rstrip() for x in s.splitlines())+('\n' if s else ''))
 rows=list(csv.DictReader((d/'timing.csv').open()));assert len(rows)==(40 if d.name=='fixed-rows' else 32 if d.name in ('640','400','fixed-grid') else 8)
 chunks=list(csv.DictReader((d/'chunks.csv').open())) if (d/'chunks.csv').exists() else []
 for x in rows:
  assert x['bitdiff']=='0' and int(x['rounds'])==16 and int(x['tokens']) in (400,496,512,528,640)
  assert float(x['mean_us'])>0 and math.isfinite(float(x['mean_us']))
  f=int(x['tokens'])//16*64*16*16*8192
  assert abs((0 if 'loadonly' in x['kernel'] else f/(float(x['mean_us'])*1e6))-float(x['tflops']))<1e-5
  if chunks:
   cs=[c for c in chunks if c['test']==x['test'] and c['slot']==x['slot']]
   assert len(cs)==10 and sum(int(c['launches']) for c in cs)==int(x['launches'])
   assert abs(sum(float(c['mean_us'])*int(c['launches']) for c in cs)/int(x['launches'])-float(x['mean_us']))<1e-6
 points=[]
 for line in (d/'telemetry.log').read_text().splitlines():
  p={k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',line)}
  if p.get('adapter')==0 and p.get('status')==0:points.append(p)
 def measure(rs):
  intervals=[(int(c['start_ms']),int(c['end_ms'])) for c in chunks if any(c['test']==x['test'] and c['slot']==x['slot'] for x in rs)] if chunks else [(int(x['start_ms']),int(x['end_ms'])) for x in rs]
  ps=[p for p in points if any(a<=p['tick']<=b for a,b in intervals)];tel={}
  for k in (1,2,73):
   vs=[p[f'sensor{k}'] for p in ps if p.get(f'sensor{k}_supported')==1]
   tel[str(k)]={'median':statistics.median(vs),'min':min(vs),'max':max(vs),'n':len(vs)} if vs else None
  f=int(rs[0]['tokens'])//16*64*16*16*8192
  mean=statistics.mean(float(x['mean_us']) for x in rs);tf=0 if 'loadonly' in rs[0]['kernel'] else f/(mean*1e6)
  return dict(mean_us=mean,tflops=tf,clock_reference_fraction=tf/(tel['1']['median']*.131072) if tel['1'] else None,slots_us=[float(x['mean_us']) for x in rs],telemetry=tel)
 summary[d.name]={}
 for test in dict.fromkeys(x['test'] for x in rows):
  rs=[x for x in rows if x['test']==test];a=measure([x for x in rs if int(x['slot'])%4 in (0,3)]);b=measure([x for x in rs if int(x['slot'])%4 in (1,2)])
  summary[d.name][test]={'A':a,'B':b,'delta_us':b['mean_us']-a['mean_us']}
  if True:
   print(d.name,test,'us',round(a['mean_us'],3),round(b['mean_us'],3),'core',a['telemetry']['1']['median'],b['telemetry']['1']['median'],'mem',a['telemetry']['2']['median'],b['telemetry']['2']['median'])
(root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
isa=[]
for file in sys.argv[2:]:
 s=Path(file).read_text()
 for name in ['model4','pair64','pair128','pair128_adjacent','pair128_loadonly','pair128_loadonly_multi','pair128_loadonly_rows']:
  if '\n'+name+':' not in s:continue
  a=s.index('\n'+name+':');b=s.index('.Lfunc_end',a)
  ops=collections.Counter(re.findall(r'^\s+((?:s_|v_|ds_|global_|flat_|scratch_|buffer_)\w+)\b',s[a:b],re.M))
  assert ops['v_wmma_f32_16x16x16_fp8_fp8']==(0 if 'loadonly' in name else 16)
  e=s.find('\n\t.globl',a+1);part=s[a:e if e>=0 else len(s)]
  compiler=dict(re.findall(r'; (NumVgprs|NumVGPRsForWavesPerEU|Occupancy): (\d+)',part))
  meta=re.search(r'\.amdhsa_kernel '+name+r'\n(.*?)\.end_amdhsa_kernel',s,re.S)[1]
  res=dict(re.findall(r'\.(amdhsa_(?:group_segment_fixed_size|private_segment_fixed_size|next_free_vgpr|next_free_sgpr))\s+(\d+)',meta))
  assert res['amdhsa_private_segment_fixed_size']=='0'
  isa.append(dict(source=Path(file).name,name=name,compiler=compiler,resources=res,opcodes=dict(ops)))
if isa:(root/'isa.json').write_text(json.dumps(isa,indent=2)+'\n')
