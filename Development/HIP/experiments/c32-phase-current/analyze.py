"""Validate trace records and summarize observed wave intervals, not wall-time shares."""
from collections import defaultdict
import csv
import json
from pathlib import Path
import statistics
import struct
import sys

folder = Path(sys.argv[1])
phases = ['whole','staging','ffn+publish','qkv+norm','attention+publish','projection','tail','initial_sync','residual_init','ffn_math','ffn_publish']
sample_stride = int(sys.argv[2]) if len(sys.argv)>2 else 5
timing = defaultdict(list)
for row in csv.DictReader((folder/'timing.csv').open()):
    timing[int(row['phase'])].append(row)
report = {'timing':{}, 'launches':{}, 'aggregate':{}}
for phase, rows in sorted(timing.items()):
    rows.sort(key=lambda r:int(r['slot']))
    assert [int(r['mode']) for r in rows] == [0,phase+1,phase+1,0]
    times = [float(r['ms']) for r in rows]
    base=(times[0]+times[3])/2; traced=(times[1]+times[2])/2
    report['timing'][phases[phase]]={'base_ms':base,'traced_ms':traced,'delta_ms':traced-base,'delta_pct':100*(traced/base-1)}
    totals=[];stages=[]
    for meta in csv.DictReader((folder/f'phase{phase}-meta.csv').open()):
        index=int(meta['launch']);groups=int(meta['groups']);values=[];perframe=[]
        for frame in range(8):
            blob=(folder/f'phase{phase}-launch{index}-frame{frame}.u32').read_bytes()
            records=list(struct.iter_unpack('<IIII',blob))
            wanted=0;current=[]
            for group in range((frame*sample_stride)%32,groups,32):
                for wave in range(4):
                    p,t,g,magic=records[(group//32)*4+wave]
                    assert magic == 0xc3200000|phase and g==group, (phase,index,frame,group,wave,magic,g)
                    assert 0 < t < 0x80000 and p <= t, (phase,index,frame,p,t)
                    if phase==0:assert p==t
                    current.append((p,t));wanted+=1
            valid=[r for r in records if r[3]]
            assert len(valid)==wanted,(phase,index,frame,len(valid),wanted)
            values.extend(current)
            perframe.append(statistics.mean(p for p,t in current))
        ps=[p for p,t in values];ts=[t for p,t in values]
        meanp=statistics.mean(ps);meant=statistics.mean(ts)
        launch=report['launches'].setdefault(str(index),{'kernel':meta['kernel'],'groups':groups,'phases':{}})
        launch['phases'][phases[phase]]={
            'samples':len(values),'phase_mean_cycles':meanp,'whole_mean_cycles':meant,
            'phase_median_cycles':statistics.median(ps),'phase_p90_cycles':sorted(ps)[int(.9*len(ps))],
            'phase_ratio_same_kernel':meanp/meant,'frame_means':perframe,
        }
        # Each launch weighted by its actual number of waves, avoiding edge rounding of sampled counts.
        stages.append(meanp*groups*4);totals.append(meant*groups*4)
    report['aggregate'][phases[phase]]={'sum_weighted_stage_cycles':sum(stages),'sum_weighted_whole_cycles':sum(totals),'ratio_same_kernel':sum(stages)/sum(totals)}
selected=[p for p in phases if p in report['timing']]
for p in selected:
    t=report['timing'][p];a=report['aggregate'][p]
    print(f'{p:20} observed stage/whole={100*a["ratio_same_kernel"]:5.1f}%  instrumentation={t["delta_ms"]:+.4f}ms ({t["delta_pct"]:+.2f}%)')
print('\nPer-launch mean cycles (phase variants are separately compiled):')
for i,row in report['launches'].items():
    print(i,row['kernel'])
    print('  '+', '.join(f'{p}={row["phases"][p]["phase_mean_cycles"]:.0f}' for p in selected))
(folder/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
