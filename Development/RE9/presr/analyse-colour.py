"""Inspect same-frame GPU captures; no inferred game tonemapping in statistics."""
from pathlib import Path
import argparse,json
import numpy as np
p=argparse.ArgumentParser();p.add_argument('directory',type=Path);args=p.parse_args();folder=args.directory

def load(name):
 m=json.loads((folder/(name+'.json')).read_text());raw=(folder/(name+'.bin')).read_bytes();fmt=m['format']
 if m['dimension']==1:return np.frombuffer(raw,dtype='<f4').astype(np.float64)
 if fmt==67:
  words=np.ndarray((m['height'],m['width']),dtype='<u4',buffer=raw,offset=m['offset'],strides=(m['row_pitch'],4))
  mant=np.stack([words&511,(words>>9)&511,(words>>18)&511],axis=-1)
  return mant*np.exp2((words>>27).astype(np.int32)[...,None]-24)
 dtype,ch={10:('<f2',4),2:('<f4',4),41:('<f4',1),54:('<f2',1)}[fmt];b=np.dtype(dtype).itemsize
 return np.ndarray((m['height'],m['width'],ch),dtype=dtype,buffer=raw,offset=m['offset'],strides=(m['row_pitch'],b*ch,b)).astype(np.float64)

report={'frame':json.loads((folder/'frame.json').read_text())};images={}
for name in ['input','proxy','neural','result','exposure']:
 if not (folder/(name+'.json')).exists():continue
 a=load(name);images[name]=a
 rgb=a[...,:3] if a.ndim==3 else a
 report[name]={'shape':list(a.shape),'finite_fraction':float(np.isfinite(a).mean()),'quantiles':np.quantile(rgb,[0,.01,.1,.5,.9,.99,1]).tolist(),'fraction_over_075':float((rgb>.75).mean()),'fraction_over_1':float((rgb>1).mean())}
 if a.ndim==3 and a.shape[-1]>=3:
  report[name]['mean_rgb']=rgb.mean((0,1)).tolist()
  report[name]['near_white_pixel_fraction']=float((rgb.min(-1)>.98).mean())
 if name=='exposure':report[name]['first_values']=a.flatten()[:16].tolist()
if 'input' in images and 'result' in images:
 original=images['input'][...,:3];result=images['result'][...,:3]
 ratio=result/np.maximum(original,1e-8)
 report['result_vs_input']={'mae':float(np.abs(original-result).mean()),'channel_ratio_median':np.median(ratio,axis=(0,1)).tolist()}
print(json.dumps(report,indent=2));(folder/'analysis.json').write_text(json.dumps(report,indent=2)+'\n')
