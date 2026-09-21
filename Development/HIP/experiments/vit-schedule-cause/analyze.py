from pathlib import Path
import csv,json,re,statistics,sys
root=Path(sys.argv[1]);asm=Path(sys.argv[2]).read_text();result={};isa={}
for m in re.finditer(r'^(probe_\w+|vit_expand_blocked_fp8_frag_bytein|vit_contract_blocked_fp8_frag):',asm,re.M):
 p=asm[m.start():asm.index('; COMPUTE_PGM_RSRC2',m.end())]
 isa[m[1]]={key:int(re.search('; '+key+': (\\d+)',p)[1]) for key in ('NumVgprs','ScratchSize','Occupancy','LDSByteSize')}
 isa[m[1]].update(wmma_static=p.count('\tv_wmma_'),load64_static=p.count('\tglobal_load_b64'),waitload_static=p.count('\ts_wait_loadcnt'))
(root/'isa.json').write_text(json.dumps(isa,indent=2)+'\n')
def telemetry(d,slots):
 points=[]
 for line in (d/'telemetry.log').read_text(encoding='utf-8-sig').splitlines():
  v=dict(re.findall(r'(\w+)=(-?\d+)',line))
  if v.get('adapter')!='0' or v.get('status')!='0' or v.get('sensor1_supported')!='1':continue
  tick=int(v['tick'])
  if any(int(r['start_ms'])<=tick<=int(r['end_ms']) for r in slots):points.append(int(v['sensor1']))
 return {'samples':len(points),'median_core_mhz':statistics.median(points) if points else None,'min_core_mhz':min(points) if points else None,'max_core_mhz':max(points) if points else None}
for d in sorted(root.iterdir()):
 if not d.is_dir() or not re.fullmatch(r'(900|1080)-(expand|contract)',d.name):continue
 rows=list(csv.DictReader((d/'schedule.csv').open()));assert len(rows)==(32 if 'expand' in d.name else 8)
 assert all(int(x['output_diff'])==0 and float(x['mean_us'])>0 for x in rows)
 assert (d/'run.log').read_text().count('bitdiff=0')==2
 variants={}
 for name in sorted(set(x['variant'] for x in rows)):
  r=[x for x in rows if x['variant']==name];base=[x for x in r if int(x['slot'])%4 in (0,3)];test=[x for x in r if int(x['slot'])%4 in (1,2)]
  b=statistics.mean(float(x['mean_us']) for x in base);t=statistics.mean(float(x['mean_us']) for x in test)
  variants[name]={'baseline_us':b,'candidate_us':t,'change_percent':100*(t/b-1),'baseline_clock':telemetry(d,base),'candidate_clock':telemetry(d,test)}
 result[d.name]=variants
assert len(result)==4
(root/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
network={}
for d in sorted(root.glob('network-*')):
 if not d.is_dir():continue
 rows=list(csv.DictReader((d/'network.csv').open()));assert len(rows)==16
 assert all(int(x['bitdiff'])==0 and int(x['replacements'])==(800 if int(x['mode']) else 0) for x in rows)
 variants={}
 for variant in ('1','2'):
  r=[x for x in rows if x['variant']==variant];base=[x for x in r if x['mode']=='0'];test=[x for x in r if x['mode']!='0']
  b=statistics.mean(float(x['mean_ms']) for x in base);t=statistics.mean(float(x['mean_ms']) for x in test)
  variants[variant]={'baseline_ms':b,'candidate_ms':t,'delta_ms':t-b,'change_percent':100*(t/b-1),'baseline_clock':telemetry(d,base),'candidate_clock':telemetry(d,test)}
 network[d.name]=variants
(root/'network-summary.json').write_text(json.dumps(network,indent=2)+'\n')
print(json.dumps({'micro':result,'network':network},indent=2))
