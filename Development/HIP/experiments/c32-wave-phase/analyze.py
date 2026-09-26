"""analyze.py <results-dir> : per-phase share of single-wave C32 per-wave cycles, by kernel role and weighted over the frame.

Share of a phase = sum_i windows_i*mean(phase cycles_i) / sum_i windows_i*mean(whole cycles_i), both from the same instrumented
run (each phase is a separate compile). Weighting by windows x per-wave cycles approximates issued work, not wall time.
"""
import csv, struct, sys, statistics
from pathlib import Path

NAMES = ['whole', 'input', 'chain_mix', 'ffn', 'feature_pack', 'qkv_norm', 'scores_exp', 'sums_prob', 'av', 'projection_store', 'tail']
d = Path(sys.argv[1])
timing = list(csv.DictReader(open(d / 'timing.csv')))


def load(phase):
    meta = list(csv.DictReader(open(d / f'phase{phase}-meta.csv')))
    out = []
    for m in meta:
        i = int(m['launch']); groups = int(m['groups']); ph, wh = [], []
        for f in range(8):
            b = (d / f'phase{phase}-launch{i}-frame{f}.u32').read_bytes()
            for k in range(0, len(b) // 16):
                c, w, win, magic = struct.unpack_from('<4I', b, k * 16)
                if magic == 0xc3210000 | phase and c < w + 64 and w:
                    ph.append(c); wh.append(w)
        out.append((m['kernel'], groups, ph, wh))
    return out


roles = {}
rows = []
for p in range(11):
    data = load(p)
    num = sum(g * statistics.fmean(ph) for _, g, ph, wh in data if ph)
    den = sum(g * statistics.fmean(wh) for _, g, ph, wh in data if wh)
    t = [float(r['ms']) for r in timing if int(r['phase']) == p]
    pert = (t[1] + t[2]) / 2 - (t[0] + t[3]) / 2 if len(t) == 4 else float('nan')
    samples = sum(len(ph) for _, _, ph, _ in data)
    rows.append((p, NAMES[p], num / den if den else 0, pert, samples))
    for k, g, ph, wh in data:
        if ph:
            r = roles.setdefault(k, {})
            r[p] = (statistics.fmean(ph), statistics.fmean(wh), g)
print(f'# {d.name}')
print('phase,name,share_of_c32_wave_cycles,instrument_ms_delta,samples')
for p, n, s, pert, cnt in rows:
    print(f'{p},{n},{s:.4f},{pert:+.4f},{cnt}')
print('\n# per kernel (mean cycles per wave; share of that kernel\'s whole in the same run)')
print('kernel,groups,whole_cycles,' + ','.join(NAMES[1:]))
for k, r in roles.items():
    g = r[0][2]; whole = r[0][1]
    print(f'{k},{g},{whole:.0f},' + ','.join(f'{r[p][0] / r[p][1]:.3f}' if p in r else '' for p in range(1, 11)))
