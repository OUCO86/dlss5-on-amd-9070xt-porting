# Per-region clock/power ledger: each config duplicates one kernel family x8 (DLSS5_HIP_DUP_PREFIX/COUNT) so that family
# dominates the frame; ADL telemetry (200 ms) gives the core clock / board power the card settles to under that family.
# Usage: analyze.py <dir with <height>-<cfg> folders>
import re,sys,statistics
from pathlib import Path
root=Path(sys.argv[1]);rows=[]
for f in sorted(root.iterdir()):
    if not (f/'run.log').exists():continue
    raw=(f/'run.log').read_bytes();log=raw.decode('utf-16') if raw[:2] in (b'\xff\xfe',b'\xfe\xff') else raw.decode('utf-8',errors='replace')
    m=re.search(r'RESULT frames=(\d+).*?mean_wall_ms=([\d.]+)',log);f0=re.search(r'frame=0 .*?wall_ms=([\d.]+)',log)
    n=int(m.group(1));mean=float(m.group(2));first=float(f0.group(1));frame=(mean*n-first)/(n-1)
    tel=(f/'telemetry.log').read_text(errors='replace').splitlines()
    samp=[l for l in tel if 'adapter=0 ' in l and 'status=0' in l]
    samp=[l for l in samp if (m19:=re.search(r'sensor19_supported=1 sensor19=(\d+)',l)) and int(m19.group(1))>=90]  # benchmark running
    samp=samp[len(samp)//4:]  # drop warm-up quarter
    def med(sid):
        v=[int(x) for x in re.findall(rf'sensor{sid}_supported=1 sensor{sid}=(\d+)',"\n".join(samp))]
        return (statistics.median(v),min(v),max(v)) if v else (None,None,None)
    mhz=med(1);w=med(73);edge=med(8);hot=med(27);act=med(19);mem=med(2)
    rows.append((f.name,frame,len(samp),mhz,w,edge,hot,act,mem))
print('| config | frame ms | samples | core MHz med (min-max) | board W med (min-max) | edge/hot °C | gfx act % | mem MHz |')
print('|---|---:|---:|---|---|---|---:|---:|')
for name,frame,ns,mhz,w,edge,hot,act,mem in rows:
    print(f'| {name} | {frame:.3f} | {ns} | {mhz[0]} ({mhz[1]}-{mhz[2]}) | {w[0]} ({w[1]}-{w[2]}) | {edge[0]}/{hot[0]} | {act[0]} | {mem[0]} |')
