"""RGB difference between base and candidate regression frames (f16 files written by benchmark_main_reuse).
usage: rgbdiff.py <base dir> <candidate dir>  -> per-frame max/mean abs diff, fraction of differing pixels, PSNR (values in [0,1])"""
import sys, numpy as np
from pathlib import Path
b,c=Path(sys.argv[1]),Path(sys.argv[2])
for f in sorted(b.glob('*frame-*.f16')):
    x=np.fromfile(f,dtype=np.float16).astype(np.float32); y=np.fromfile(c/f.name,dtype=np.float16).astype(np.float32)
    d=np.abs(x-y); mse=float(np.mean((x-y)**2)); psnr=10*np.log10(1.0/mse) if mse>0 else float('inf')
    print(f'{f.name}: max {d.max():.5f} mean {d.mean():.2e} differing {np.mean(d>0)*100:.2f}% >1/255 {np.mean(d>1/255)*100:.3f}% PSNR {psnr:.1f} dB')
