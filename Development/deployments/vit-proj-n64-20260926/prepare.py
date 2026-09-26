"""Generate vit-wide-deep.hip exactly as hip/build-modules.ps1 concatenates it (HIP_ISA_HALF 1 + row defines + sources, each
followed by a newline)."""
from pathlib import Path
R=Path(__file__).resolve().parents[3];H=R/'hip';D=Path(__file__).resolve().parent
defines,sources=['HIP_PREPACKED_WEIGHTS 1','HIP_BRANCHLESS_F 1'],['deep_fast.hip','vit_wide_deep.inc']
recipe=(H/'build-modules.ps1').read_text()
assert "name = 'vit-wide-deep'" in recipe and all(f"'{d}'" in recipe for d in defines)
text='#define HIP_ISA_HALF 1\n'+''.join(f'#define {d}\n' for d in defines)+''.join((H/s).read_text()+'\n' for s in sources)
(D/'vit-wide-deep.hip').write_bytes(text.encode());print('vit-wide-deep',len(text))
