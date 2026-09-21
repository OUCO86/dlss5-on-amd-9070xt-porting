"""Compare selected ELF64 function bodies, excluding metadata/padding outside symbols."""
from pathlib import Path
import struct,sys,json

def functions(path):
 b=Path(path).read_bytes();assert b[:6]==b'\x7fELF\x02\x01'
 off=struct.unpack_from('<Q',b,40)[0];size,num=struct.unpack_from('<HH',b,58)
 sections=[struct.unpack_from('<IIQQQQIIQQ',b,off+i*size) for i in range(num)];out={}
 for sh in sections:
  if sh[1]!=2:continue
  st=sections[sh[6]];names=b[st[4]:st[4]+st[5]]
  for i in range(sh[4],sh[4]+sh[5],sh[9]):
   n,info,_,idx,value,count=struct.unpack_from('<IBBHQQ',b,i)
   if info&15!=2 or idx>=len(sections):continue
   name=names[n:names.find(b'\0',n)].decode();sec=sections[idx];start=sec[4]+value-sec[3];out[name]=b[start:start+count]
 return out

a,b=map(functions,sys.argv[1:3]);result=[]
for name in a:
 if ('c128_project' in name or 'c256_frag_project' in name) and 'bytein_fb' in name:
  result.append(dict(name=name,baseline_bytes=len(a[name]),candidate_bytes=len(b[name]),identical=a[name]==b[name]))
assert len(result)==4
print(json.dumps(result,indent=2))
