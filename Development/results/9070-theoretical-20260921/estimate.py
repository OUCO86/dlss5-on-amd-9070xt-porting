"""Analytic principal-matrix FLOPs, not measured instruction/DRAM counters.
2 operations per multiply-accumulate. Includes logical grouped matmuls and window
padding, excludes diagonal-emulation MMAs, normalization/activations, scalar ops,
codec, movement, synchronization, and device instruction-level redundant lanes.
"""
import json
from pathlib import Path
rows={}
shifts=[0,3,1,2,0,3,1,2];dec=[0,3,1,2,0,3,1,2,0,3,1,2,0,3,1,2,1,2,0,3,1,2,0,3,1,2,0,3,1,2]
for tier,W,H,n,ms in [(900,1600,960,400,13.206886719),(1080,1920,1152,640,18.688054688)]:
 stages={}
 def add(name,mac,precision='fp8'):
  key=name+'/'+precision;stages[key]=stages.get(key,0)+2*mac
 def block(b,c,w,h,shift):
  if b in [42,43,46]:return
  sx=4 if shift&1 else 0;sy=4 if shift&2 else 0
  t=(w+2*sx)*(h+2*sy) if c==32 else ((w+sx+7)//8*8)*((h+sy+7)//8*8)
  if c==32:add('C32',t*(12*c*c+128*c))
  elif c<512:add(f'C{c}',t*(9*c*c+128*c+128*c)) # expand4C², grouped contract128C, projectC²,QKV3C²,attn-projectC²,QK/AV128C
  else:
   add('C512',t*(512*512+8*64*256),'fp16') # mix and grouped expansion
   add('C512',t*(8*256*64+512*512+3*512*512+512*512+128*512))
 # input/output full-raster C32, middle half-raster C32 chains
 block(0,32,W,H,0);block(70,32,W,H,3)
 for b in range(1,5):block(b,32,W//2,H//2,shifts[b-1])
 for c,start,end,div in [(64,5,9,4),(128,9,15,8),(256,15,23,16),(512,23,31,32)]:
  for b in range(start,end):block(b,c,W//div,H//div,shifts[b-start])
 for c,start,end,div in [(512,40,48,32),(256,48,56,16),(128,56,62,8),(64,62,66,4),(32,66,70,2)]:
  for b in range(start,end):block(b,c,W//div,H//div,dec[b-40])
 add('ViT',8*n*(2*1024*4096+1024*1024))
 add('ViT',8*n*(3*1024*1024),'fp16')
 add('ViT-attention',8*2*n*n*1024)
 add('input-head',W*H*16*32,'fp16')
 # Downsample projects execute at lower output grid; decoder projects at low-res input grid.
 for c,div in [(32,4),(64,8),(128,16),(256,32)]:add('down',W//div*(H//div)*c*(2*c),'fp16')
 add('down',n*512*1024,'fp16')
 add('up',n*1024*512,'fp16')
 for ic,oc,div in [(512,256,32),(256,128,16),(128,64,8),(64,32,4)]:add('up',W//div*(H//div)*ic*oc,'fp16')
 add('RGB',W*H*32*3,'fp32')
 f8=sum(v for k,v in stages.items() if k.endswith('/fp8'));f16=sum(v for k,v in stages.items() if k.endswith('/fp16'));f32=sum(v for k,v in stages.items() if k.endswith('/fp32'));total=f8+f16+f32
 ideal=f8/389e12*1000+f16/195e12*1000+f32/48.7e12*1000
 rows[tier]=dict(stages_GFLOP={k:v/1e9 for k,v in stages.items()},total_GFLOP=total/1e9,fp8_GFLOP=f8/1e9,fp16_GFLOP=f16/1e9,measured_ms=ms,effective_TFLOPS=total/ms/1e9,fp8_peak_ratio=total/ms/1e9/389,optimistic_matrix_ms=ideal,actual_over_optimistic=ms/ideal)
rows['single_ffn']=dict(FLOP=2*400*1024*4096,measured_us=34.5,ideal_fp8_us=2*400*1024*4096/389e12*1e6,effective_TFLOPS=2*400*1024*4096/34.5e-6/1e12)
Path(__file__).with_name('estimate.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
