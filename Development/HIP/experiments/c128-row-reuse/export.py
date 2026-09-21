from pathlib import Path
import sys,numpy as np
w=np.fromfile(sys.argv[1],'<f2').astype(np.float32)[:512*128]
levels=np.array([(b&7)/512 if b<8 else (1+(b&7)/8)*2.**(((b>>3)&15)-7) for b in range(127)],np.float32)
ix=np.searchsorted(levels,np.abs(w));assert np.array_equal(levels[ix],np.abs(w))
p=Path(sys.argv[2]);p.mkdir(exist_ok=True);(ix.astype(np.uint8)|(np.signbit(w).astype(np.uint8)*128)).tofile(p/'weight.fp8')
rng=np.random.default_rng(20260921);rng.choice(np.array([0x30,0x38,0x40,0xb0,0xb8,0xc0],np.uint8),size=26624*128).tofile(p/'input.fp8')
