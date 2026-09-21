"""Read uncompressed RDF3 containers and observed RGP DerivedSpmCtr v1 schema.
Cross-check derived ratios against referenced raw derived-counter arrays. No SQTT
instruction decode, no guessed clock conversion, no per-frame DRAM claim.
"""
from pathlib import Path
import struct,json,sys,hashlib,math
b=Path(sys.argv[1]).read_bytes();magic,version,reserved,off,size=struct.unpack_from('<8sIIQQ',b)
assert magic==b'AMD_RDF ' and version==3 and reserved==0 and size%64==0 and off+size<=len(b)
chunks=[]
for p in range(off,off+size,64):
 n,compression,v,ho,hs,do,ds,raw=struct.unpack_from('<16sIIQQQQQ',b,p);n=n.rstrip(b'\0').decode()
 assert ho+hs<=len(b) and do+ds<=len(b)
 if n in ['SpmSession','DerivedSpmCtr','TraceConfig','ApiInfo']:
  assert compression==0,(n,compression)
  chunks.append((n,v,b[ho:ho+hs],b[do:do+ds]))
session=next(x for x in chunks if x[0]=='SpmSession');assert session[1]==2
pci,flags,interval,count,counters=struct.unpack('<5I',session[2]);assert len(session[3])==count*8
values={};meta={}
for name,v,h,d in chunks:
 if name!='DerivedSpmCtr':continue
 assert v==1 and len(h)==24
 gpu,idx,kind,unit,nlen,dlen=struct.unpack('<6I',h);assert kind in [0,2,3]
 tail={0:0,2:8,3:12}[kind];assert len(d)==8*count+tail+nlen+dlen
 a=struct.unpack('<'+str(count)+'d',d[:8*count]);assert all(math.isfinite(x) for x in a)
 label=d[8*count+tail:8*count+tail+nlen].decode();desc=d[-dlen:].decode()
 refs=struct.unpack('<'+'I'*(tail//4),d[8*count:8*count+tail]) if tail else ()
 values[idx]=a;meta[idx]=dict(name=label,kind=kind,unit=unit,references=refs,description=desc)
checks={}
for idx,m in meta.items():
 if m['kind']==0:continue
 refs=m['references'];den=values[refs[0]];num=values[refs[1]];expected=[100*y/x if x else 0 for x,y in zip(den,num)]
 # Provider may clamp ratio counters to100 (observed sample jitter).
 err=max(abs(min(100.,max(0.,x))-y) for x,y in zip(expected,values[idx]));checks[m['name']]=err
 assert err<1.e-5,(m['name'],err)
rows=[]
for idx,m in meta.items():
 a=values[idx];row=dict(m,index=idx,min=min(a),max=max(a))
 if m['kind']==0:row['sum']=sum(a)
 else:
  den=sum(values[m['references'][0]]);num=sum(values[m['references'][1]]);row['weighted_percent']=100*num/den if den else 0
 rows.append(row)
config=json.loads(next(x[3] for x in chunks if x[0]=='TraceConfig').rstrip(b'\0'))
result=dict(trace_sha256=hashlib.sha256(b).hexdigest(),api_data=next(x[3].hex() for x in chunks if x[0]=='ApiInfo'),sample_count=count,sample_interval=interval,trace_config=config,ratio_checks=checks,counters=rows)
Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+'\n')
print('samples',count,'render_ops',config['controller']['config']['captureRenderOpCount'])
for row in rows:
 if 'weighted_percent' in row:print(row['name'],round(row['weighted_percent'],3))
