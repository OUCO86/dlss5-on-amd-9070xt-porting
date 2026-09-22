"""Read the actual HSACO AMDGPU MsgPack note, independently of its .s listing."""
from pathlib import Path
import struct,msgpack,json,sys
b=Path(sys.argv[1]).read_bytes();assert b[:5]==b'\x7fELF\x02'
off=struct.unpack_from('<Q',b,40)[0];ents,n=struct.unpack_from('<HH',b,58);out={}
for i in range(n):
 sec=struct.unpack_from('<IIQQQQIIQQ',b,off+i*ents)
 if sec[1]!=7:continue
 data=b[sec[4]:sec[4]+sec[5]];p=0
 while p+12<=len(data):
  ns,ds,t=struct.unpack_from('<III',data,p);p+=12;name=data[p:p+ns].rstrip(b'\0');p+=(ns+3)//4*4;desc=data[p:p+ds];p+=(ds+3)//4*4
  if name==b'AMDGPU' and t==32:
   m=msgpack.unpackb(desc,raw=False)
   for k in m['amdhsa.kernels']:
    if k['.name'].startswith('probe_') or k['.name']=='vit_expand_blocked_fp8_frag_bytein':out[k['.name']]={x:v for x,v in k.items() if x!='.args'}
assert out
Path(sys.argv[2]).write_text(json.dumps(out,indent=2)+'\n')
