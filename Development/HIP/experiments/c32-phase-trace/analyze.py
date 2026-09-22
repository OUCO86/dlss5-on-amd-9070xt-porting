"""Per-wave phase accounting from in-kernel SHADER_CYCLES stamps.

usage: analyze.py <dir with trace-<i>.u64 + trace-groups.txt> [clock_mhz]
Each wave record: 10 stamps (entry, staged, ffn, ffn_written, qkv, scores, prob, av, proj, end), barrier wait cycles, barrier count.
The last traced frame's data is what the buffer holds (every frame overwrites the same slots)."""
import sys, struct, statistics
from pathlib import Path
d = Path(sys.argv[1]); mhz = float(sys.argv[2]) if len(sys.argv) > 2 else None
NAMES = ['prefix_finish_main8', 'mapped', 'chain', 'chain', 'chain_finish_dcrop', 'mapped', 'chain', 'chain', 'chain_finish', 'post_merge_head']
PHASES = ['staging', 'ffn', 'ffn_write+sync', 'qkv(3 parts+norm)', 'scores', 'softmax/prob', 'av', 'projection/output', 'tail']
groups = {int(a): int(b) for a, b in (l.split() for l in (d / 'trace-groups.txt').read_text().split('\n') if l.strip())}
REC = 12
grand = {}
for i in sorted(groups):
    raw = (d / f'trace-{i}.u64').read_bytes()
    n = groups[i] * 4
    vals = struct.unpack(f'<{n*REC}Q', raw[:n*REC*8])
    recs = [vals[j*REC:(j+1)*REC] for j in range(n)]
    recs = [r for r in recs if r[0] and r[9] > r[0]]  # waves that ran and wrote
    if not recs: print(f'launch {i} ({NAMES[i]}): no records'); continue
    per = [[r[k+1]-r[k] for k in range(9)] + [r[10], r[11], r[9]-r[0]] for r in recs]
    cols = list(zip(*per))
    med = [statistics.median(c) for c in cols]; mean = [statistics.mean(c) for c in cols]
    total_mean = mean[11]
    print(f'\nlaunch {i} {NAMES[i]:22} groups={groups[i]} waves={len(recs)} mean_total={total_mean:,.0f} cyc median_total={med[11]:,.0f}' + (f' (~{total_mean/mhz/1e3*1e3:,.1f} us @ {mhz}MHz)' if mhz else ''))
    print(f'  {"phase":22} {"mean":>10} {"median":>10} {"p90":>10} {"share":>6}')
    for k, name in enumerate(PHASES):
        c = sorted(cols[k]); p90 = c[int(len(c)*0.9)]
        print(f'  {name:22} {mean[k]:>10,.0f} {med[k]:>10,.0f} {p90:>10,.0f} {mean[k]/total_mean*100:>5.1f}%')
    print(f'  {"barrier wait (in above)":22} {mean[9]:>10,.0f} {med[9]:>10,.0f} {"":>10} {mean[9]/total_mean*100:>5.1f}%  barriers/wave={mean[10]:.1f}')
    grand[i] = dict(name=NAMES[i], waves=len(recs), mean=mean, total=total_mean)
# whole-C32 weighted share by wave-cycles
tot = sum(g['total']*g['waves'] for g in grand.values())
print('\n== C32 all launches, share of summed wave-cycles ==')
for k, name in enumerate(PHASES):
    print(f'  {name:22} {sum(g["mean"][k]*g["waves"] for g in grand.values())/tot*100:5.1f}%')
print(f'  {"barrier wait (in above)":22} {sum(g["mean"][9]*g["waves"] for g in grand.values())/tot*100:5.1f}%')
