from pathlib import Path
import json
root=Path(__file__).resolve().parents[4]
source=root/'Development/results/wmma-pitch-gap-20260922'
out=root/'Development/results/wmma-page-gap-20260922'
# Count distinct 128-byte address regions per issued load/store, not actual bytes transferred.
a_count=b_count=0
for k in range(0,1024,16):
 a_count+=len({((lane%16)*1024+k+(lane//16)*8)//128 for lane in range(32)})
 for n in range(4):
  b_count+=len({(((n*32+k//32)*512+(((k%32)//16*2+lane//16)*16+lane%16)*8)//128) for lane in range(32)})
stores=sum(len({(((lane//16*8+e)*4096+n*16+lane%16)//128) for lane in range(32)}) for n in range(4) for e in range(8))
assert (a_count,b_count,stores)==(1024,512,64)
rows=[]
for name,tail in [('real-vit-1080.json',stores),('counter-1024-16384.json',1)]:
 j=json.loads((source/name).read_text());cs={x['index']:x for x in j['counters']}
 l0=next(x for x in j['counters'] if x['name']=='L0 cache hit');l2=next(x for x in j['counters'] if x['name']=='L2 cache hit')
 count=j['trace_config']['controller']['config']['captureRenderOpCount'];assert count==64
 requests=cs[l0['references'][0]]['sum'];predicted=count*2560*(a_count+b_count+tail);assert requests==predicted
 fetch=next(x['sum'] for x in j['counters'] if x['name']=='Fetch size')
 rows.append(dict(source=name,trace_sha256=j['trace_sha256'],capture_dispatches=count,waves_per_dispatch=2560,A_128B_regions_per_wave=a_count,B_128B_regions_per_wave=b_count,tail_128B_regions_per_wave=tail,predicted_requests=predicted,reported_L0_requests=requests,logical_read_MiB_per_dispatch=2560*64*5*32*8/2**20,request_coverage_read_MiB_per_dispatch=2560*(a_count+b_count)*128/2**20,request_coverage_total_MiB_per_dispatch=requests/count*128/2**20,L2_request_coverage_MiB_per_dispatch=cs[l2['references'][0]]['sum']/count*128/2**20,reported_Fetch_size_MiB_per_dispatch=fetch/count/2**20))
(out/'request-account.json').write_text(json.dumps(rows,indent=2)+'\n')
for row in rows:print(row)
