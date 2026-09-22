from pathlib import Path
import re,json,sys
s=Path(sys.argv[1]).read_text();out={}
names=['vit_expand_blocked_fp8_frag_bytein']+['probe_'+n+u for n in ['m16n128_row','m32n64_row','m16n128_tile','m32n64_tile'] for u in ['', '_u2']]
for name in names:
 if '\n'+name+':' not in s:continue
 a=s.index('\n'+name+':');b=s.find('\n\t.protected',a+1);text=s[a:b if b>=0 else len(s)]
 fields={}
 for key in ['NumVgprs','ScratchSize','Occupancy']:
  m=re.search(r'; '+key+r': ([0-9]+)',text);fields[key]=int(m.group(1)) if m else None
 fields['blocks']=[]
 for block in re.split(r'(?=^\.LBB\d+_\d+:)',text,flags=re.M):
  if 'v_wmma_' in block:
   fields['blocks'].append({'label':block.splitlines()[0],'wmma':len(re.findall(r'^\s*v_wmma_',block,re.M)),'load64':len(re.findall(r'^\s*global_load_b64',block,re.M)),'load32':len(re.findall(r'^\s*global_load_b32',block,re.M))})
 out[name]=fields
Path(sys.argv[2]).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
