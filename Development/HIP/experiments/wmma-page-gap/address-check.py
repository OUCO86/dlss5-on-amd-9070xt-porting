from pathlib import Path
import json
out=Path(__file__).resolve().parents[3]/'results/wmma-page-gap-20260922';out.mkdir(exist_ok=True)
rows=[]
for span in (64,1024):
 for mix in (0,256,512,768,1024,2048,3072,3840):
  high_changes=0;set_equal=True;unique=0
  for tile in range(256):
   ref={};changed={}
   for k in range(0,span,16):
    for g in range(2):
     for r in range(16):
      off=(k//32)*512+(((k%32)//16*2+g)*16+r)*8
      a=tile*16384+off;b=tile*16384+(off^((tile*256)&mix))
      assert a%8==b%8==0 and tile*16384<=b<(tile+1)*16384
      assert a not in ref and b not in changed
      ref[a]=1;changed[b]=1;high_changes+=(a>>12)!=(b>>12)
   set_equal&=ref.keys()==changed.keys();unique+=len(changed)*8
  assert high_changes==0 and unique==span*4096
  if span==1024 or mix<1024:assert set_equal
  rows.append(dict(span=span,mix=mix,logical_unique_bytes=unique,high_4k_changes=high_changes,exact_address_set_equal=set_equal))
(out/'address-check.json').write_text(json.dumps(rows,indent=2)+'\n');print('16 mappings verified: alignment/bijection/high address bits; full-span exact set unchanged')
