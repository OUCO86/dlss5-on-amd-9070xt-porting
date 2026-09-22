"""Launch-level occupancy from per-wave real-time stamps (record slots 14 = entry, 15 = exit, 100MHz ticks).

usage: analyze.py <dir with trace-<i>.u64 + trace-groups.txt> <waves_per_group> <resident_waves_per_simd> [cus=64] [simd_per_cu=4]
Per launch: span, summed busy, throughput-bound time (busy/slots), utilisation, mean concurrency, ramp (until 90% of peak
concurrency), tail (after the last drop below 50% of peak), and the effective core clock implied by the cycle stamps."""
import sys, struct, statistics
from pathlib import Path
d=Path(sys.argv[1]); wpg=int(sys.argv[2]); res=int(sys.argv[3]); cus=int(sys.argv[4]) if len(sys.argv)>4 else 64; spc=int(sys.argv[5]) if len(sys.argv)>5 else 4
slots=cus*spc*res; REC=16; TICK=0.01  # us per tick
groups={int(a):int(b) for a,b in (l.split() for l in (d/'trace-groups.txt').read_text().split('\n') if l.strip())}
tot_span=tot_busy=tot_ramp=tot_tail=0.0
print(f'slots={slots} ({cus} CU x {spc} SIMD x {res} waves)')
print(f'{"launch":>6} {"groups":>6} {"waves":>6} {"span us":>8} {"busy/slot":>9} {"util":>5} {"conc":>6} {"ramp":>6} {"steady":>7} {"tail":>6} {"wave us":>7} {"MHz":>5}')
for i in sorted(groups):
    raw=(d/f'trace-{i}.u64').read_bytes(); n=groups[i]*wpg
    vals=struct.unpack(f'<{n*REC}Q',raw[:n*REC*8]); recs=[vals[j*REC:(j+1)*REC] for j in range(n)]
    recs=[r for r in recs if r[14] and r[15]>r[14]]
    if not recs: print(f'{i:>6} no records'); continue
    t0=min(r[14] for r in recs); t1=max(r[15] for r in recs); span=(t1-t0)*TICK
    busy=sum(r[15]-r[14] for r in recs)*TICK; thr=busy/slots
    ev=sorted([(r[14],1) for r in recs]+[(r[15],-1) for r in recs])
    # concurrency curve
    cur=0;peak=0;curve=[]
    for t,dlt in ev: cur+=dlt;peak=max(peak,cur);curve.append((t,cur))
    ramp=next(t for t,c in curve if c>=0.9*peak); ramp=(ramp-t0)*TICK
    last_hi=max(t for t,c in curve if c>=0.5*peak); tail=(t1-last_hi)*TICK
    steady=span-ramp-tail
    # per-wave duration & implied clock
    cyc_end=next(k for k in (9,8,5) if recs[0][k])  # end cycle stamp (C32: 9, mh_fused: 8, mh_fast: 5); C32 slots 10/11 are staging sub-stamps
    wave_us=statistics.mean((r[15]-r[14])*TICK for r in recs)
    mhz=statistics.median((r[cyc_end]-r[0])/((r[15]-r[14])*TICK) for r in recs if r[cyc_end]>r[0] and r[15]>r[14])
    print(f'{i:>6} {groups[i]:>6} {len(recs):>6} {span:>8.1f} {thr:>9.1f} {busy/(span*slots):>5.2f} {busy/span:>6.0f} {ramp:>6.1f} {steady:>7.1f} {tail:>6.1f} {wave_us:>7.1f} {mhz:>5.0f}')
    tot_span+=span;tot_busy+=busy;tot_ramp+=ramp;tot_tail+=tail
print(f'sum: span {tot_span:.1f} us, throughput-bound {tot_busy/slots:.1f} us ({tot_busy/slots/tot_span*100:.0f}%), ramp {tot_ramp:.1f} ({tot_ramp/tot_span*100:.0f}%), tail {tot_tail:.1f} ({tot_tail/tot_span*100:.0f}%)')
