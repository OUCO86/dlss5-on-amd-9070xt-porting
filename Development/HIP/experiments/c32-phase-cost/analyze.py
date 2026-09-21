from pathlib import Path
import csv,json,sys,math,re
root=Path(sys.argv[1]);result={}
for d in sorted(root.iterdir()):
 if not d.is_dir() or not re.fullmatch(r'(900|1080)-(prefix|chain|post)',d.name):continue
 rows=list(csv.DictReader((d/'phase.csv').open()));assert len(rows)==84,(d,len(rows))
 assert all(int(r['byte_diff'])==0 and int(r['checked_bytes'])>0 and math.isfinite(float(r['mean_us'])) for r in rows)
 log=(d/'run.log').read_text(encoding='utf-8-sig');assert 'PASS C32 phase controls' in log and log.count('bitdiff=0')==2
 vrows=[]
 if(d/'phase-packv.csv').exists():
  vrows=list(csv.DictReader((d/'phase-packv.csv').open()));assert len(vrows)==12
  assert all(int(r['byte_diff'])==0 and int(r['checked_bytes'])>0 for r in vrows)
  vlog=(d/'run-packv.log').read_text(encoding='utf-8-sig');assert 'PASS C32 phase controls' in vlog and vlog.count('bitdiff=0')==2
 phases={}
 for phase in (('ffn','pack','qkv','scores','norm','av','project')+('packv',) if vrows else ('ffn','pack','qkv','scores','norm','av','project')):
  comparisons=[]
  for comparison in range(3):
   r=sorted((x for x in rows+vrows if x['phase']==phase and int(x['comparison'])==comparison),key=lambda x:int(x['slot']));assert len(r)==4
   values=[float(x['mean_us']) for x in r];base=(values[0]+values[3])/2;test=(values[1]+values[2])/2
   comparisons.append({'slots_us':values,'base_us':base,'test_us':test,'delta_us':test-base})
  calibration=100*comparisons[0]['delta_us']/comparisons[0]['base_us']
  phases[phase]={'calibration_percent':calibration,'extra_one_us':comparisons[1]['delta_us'],'extra_three_us':comparisons[2]['delta_us'],'per_extra_from_three_us':comparisons[2]['delta_us']/3,'comparisons':comparisons,'note':'Controlled hot-repeat marginal cost; not a native phase duration or additive time share.'}
 result[d.name]={'validated_slots':len(rows)+len(vrows),'checked_bytes_per_slot':int(rows[0]['checked_bytes']),'raw_network_checks':4 if vrows else 2,'phases':phases}
 (d/'summary.json').write_text(json.dumps(result[d.name],indent=2)+'\n')
(root/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
print('validated cases',len(result),'slots',sum(x['validated_slots'] for x in result.values()))
