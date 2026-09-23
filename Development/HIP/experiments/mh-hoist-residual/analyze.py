"""Module-set ABBA summary (fence-scope-all host csv): per test, mean of the 4 base slots vs the 4 variant slots.
usage: analyze.py <dir with <height>/network.csv ...>"""
import sys, csv, re, statistics
from pathlib import Path
d=Path(sys.argv[1])
for h in sorted(p.name for p in d.iterdir() if p.is_dir() and (p/'network.csv').exists()):
    rows=list(csv.DictReader(open(d/h/'network.csv')))
    tel=(d/h/'telemetry.log').read_text(errors='ignore') if (d/h/'telemetry.log').exists() else ''
    mhz=[int(m) for m in re.findall(r'adapter=1 name=AMD Radeon RX 9070 XT status=0 sensor1_supported=1 sensor1=(\d+)',tel)]
    for t in sorted(set(r['test'] for r in rows)):
        base=[float(r['wall_ms']) for r in rows if r['test']==t and r['mode']=='0']
        var=[float(r['wall_ms']) for r in rows if r['test']==t and r['mode']!='0']
        bd=sum(int(r['bitdiff']) for r in rows if r['test']==t)
        b=statistics.mean(base); v=statistics.mean(var)
        print(f'{h} test{t}: base {b:.3f} variant {v:.3f} delta {v-b:+.3f} ms ({(v-b)/b*100:+.2f}%) no_overlap={max(var)<min(base) or min(var)>max(base)} bitdiff={bd}'+(f' core median {statistics.median(mhz):.0f}MHz' if mhz else ''))
