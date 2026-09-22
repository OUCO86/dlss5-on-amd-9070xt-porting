from pathlib import Path
import csv, json, re, collections, statistics, sys, math

out=Path(sys.argv[1]);summary={}
for d in sorted(out.iterdir()):
 if not d.is_dir():continue
 file=d/('fused.csv' if d.name.startswith('fused-') else 'network.csv')
 if not file.exists():continue
 for p in d.iterdir():
  if p.is_file() and p.read_bytes().startswith((b'\xff\xfe',b'\xfe\xff')):p.write_text(p.read_bytes().decode('utf-16'))
 rows=list(csv.DictReader(file.open()));fused=file.name=='fused.csv';assert len(rows)==(8 if fused or d.name.startswith('retain-') else 24)
 if fused:
  for x in rows:
   assert x['byte_diff']=='0' and int(x['checked_bytes'])>0 and int(x['launches'])>0
   x.update(test=x['mode'],mode=x['mode'] if x['candidate']=='1' else '0',wall_ms=str(float(x['mean_us'])/1000))
 for x in rows:
  if not fused:assert x['bitdiff']=='0' and int(x['calls'])==int(x['frames'])*10
  assert math.isfinite(float(x['wall_ms'])) and float(x['wall_ms'])>0
 points=[]
 for line in (d/'telemetry.log').read_text().splitlines():
  p={k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',line)}
  if p.get('adapter')==0 and p.get('status')==0:points.append(p)
 def measure(rs):
  ps=[p for p in points if any(int(x['start_ms'])<=p['tick']<=int(x['end_ms']) for x in rs)];tel={}
  for k in (1,2,73):
   vs=[p[f'sensor{k}'] for p in ps if p.get(f'sensor{k}_supported')==1]
   tel[str(k)]={'median':statistics.median(vs),'min':min(vs),'max':max(vs),'n':len(vs)} if vs else None
  return dict(mean_ms=statistics.mean(float(x['wall_ms']) for x in rs),slots_ms=[float(x['wall_ms']) for x in rs],telemetry=tel)
 summary[d.name]={}
 for test in dict.fromkeys(x['test'] for x in rows):
  rs=[x for x in rows if x['test']==test];a=measure([x for x in rs if x['mode']=='0']);b=measure([x for x in rs if x['mode']!='0'])
  summary[d.name][test]={'A':a,'B':b,'delta_ms':b['mean_ms']-a['mean_ms']}
  print(d.name,test,round(a['mean_ms'],6),round(b['mean_ms'],6),'delta',round(b['mean_ms']-a['mean_ms'],6),'core',a['telemetry']['1']['median'],b['telemetry']['1']['median'])
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
isa=[]
for path in sys.argv[2:]:
 s=Path(path).read_text()
 for base in ['c32_fast_ffn_attention_fused_half_prefix_finish_main8','c32_fast_ffn_attention_fused_half_chain','c32_post_merge_head_half']:
  for mode in range(5):
   name=base+(f'_pair{mode}' if mode else '')
   if '\n'+name+':' not in s:continue
   a=s.index('\n'+name+':');b=s.index('.Lfunc_end',a)
   ops=collections.Counter(re.findall(r'^\s+((?:s_|v_|ds_|global_|flat_|scratch_|buffer_)\w+)\b',s[a:b],re.M))
   meta=re.search(r'\.amdhsa_kernel '+name+r'\n(.*?)\.end_amdhsa_kernel',s,re.S)[1]
   res=dict(re.findall(r'\.(amdhsa_(?:group_segment_fixed_size|private_segment_fixed_size|next_free_vgpr|next_free_sgpr))\s+(\d+)',meta))
   e=s.find('\n\t.globl',a+1);part=s[a:e if e>=0 else len(s)]
   compiler=dict(re.findall(r'; (NumVgprs|NumVGPRsForWavesPerEU|Occupancy): (\d+)',part))
   isa.append(dict(source=Path(path).name,name=name,mode=mode,static_instructions=sum(ops.values()),resources=res,compiler=compiler,opcodes=dict(ops)))
if isa:(out/'isa.json').write_text(json.dumps(isa,indent=2)+'\n')
