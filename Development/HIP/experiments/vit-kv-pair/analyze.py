"""Analyze raw HDR output differences, display previews and full-frame ABBA timings."""
from pathlib import Path
import csv,json,sys
import numpy as np
source=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
def read(p):return np.fromfile(p,dtype='<f2').astype(np.float32).reshape(720,1296,4)[:,:,:3]
def display(a):
 a=np.clip(a,0,1);return np.where(a<=.0031308,a*12.92,1.055*a**(1/2.4)-.055)
def metrics(a,b):
 d=np.abs(a-b);ad,bd=display(a),display(b);e=ad-bd
 return dict(finite=bool(np.isfinite(a).all() and np.isfinite(b).all()),raw_mae=float(d.mean()),raw_max=float(d.max()),raw_p99=float(np.quantile(d,.99)),relative_rmse=float(np.sqrt(np.sum(d*d)/np.sum(a*a))),display_mae_255=float(np.abs(e).mean()*255),display_psnr_db=float(-10*np.log10(np.mean(e*e))))
def rows(p):return list(csv.DictReader(p.open(encoding='utf-8-sig')))
result={'timing':[],'quality':[],'marginal':[]}
for h in [900,1080]:
 r=[rows(source/f'vitpair-{h}-{i}-summary.csv')[0] for i in range(4)]
 assert r[0]['hash']==r[3]['hash'] and r[1]['hash']==r[2]['hash']
 base=np.mean([float(r[i]['median_ms']) for i in [0,3]]);pair=np.mean([float(r[i]['median_ms']) for i in [1,2]])
 result['timing'].append(dict(height=h,base_ms=float(base),pair_ms=float(pair),saved_ms=float(base-pair),reduction_percent=float((base-pair)/base*100),base_drift_ms=abs(float(r[0]['median_ms'])-float(r[3]['median_ms']))))
 for pattern in [0,1,2]:
  a,b=[read(source/f'vitpair-quality-{h}-{pattern}-{v}.f16') for v in ['base','pair']]
  result['quality'].append(dict(height=h,pattern=pattern,**metrics(a,b)))
 for v in ['base','pair']:
  p=source/f'vitpair-marginal-{h}-{v}-summary.csv'
  if not p.exists():continue
  r=rows(p);assert len({x['hash'] for x in r})==1
  t=[float(x['median_ms']) for x in r];result['marginal'].append(dict(height=h,variant=v,extra_attention_ms=t[1]-(t[0]+t[2])/2,baseline_drift_ms=abs(t[2]-t[0])))
(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
for h in [900,1080]:
 a,b=[display(read(source/f'vitpair-quality-{h}-0-{v}.f16')) for v in ['base','pair']]
 fig,ax=plt.subplots(2,3,figsize=(15,8));ims=[a,b,np.clip(np.abs(a-b)*8,0,1)]
 for i,(im,title) in enumerate(zip(ims,['Baseline','Pair-mean K/V','Absolute difference x8'])):
  ax[0,i].imshow(im);ax[0,i].set_title(title);ax[1,i].imshow(im[25:430,700:1080]);
 for axis in ax.flat:axis.axis('off')
 fig.suptitle(f'{h}p network - frozen HDR capture; preview clipped to SDR / sRGB')
 fig.tight_layout();fig.savefig(out/f'comparison-{h}.png',dpi=120);plt.close(fig)
