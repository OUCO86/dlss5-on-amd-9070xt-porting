"""Generate c512-m32-mh.hip / c512-m32-deep.hip exactly as hip/build-modules.ps1 concatenates them (HIP_ISA_HALF 1 +
row defines + sources, each followed by a newline)."""
from pathlib import Path
R=Path(__file__).resolve().parents[3];H=R/'hip';D=Path(__file__).resolve().parent
rows={'c512-m32-mh':(['HIP_PREPACKED_WEIGHTS 1','HIP_FFN_HOIST_RES 2','HIP_PDL_KERNELS 0'],['multihead_fast_padded.hip','c512_m32_mh.inc']),
      'c512-m32-deep':(['HIP_PREPACKED_WEIGHTS 1','HIP_BRANCHLESS_F 1'],['deep_fast.hip','c512_m32_deep.inc'])}
recipe=(H/'build-modules.ps1').read_text()
for name,(defines,sources) in rows.items():
 assert f"name = '{name}'" in recipe and all(f"'{d}'" in recipe for d in defines)
 text='#define HIP_ISA_HALF 1\n'+''.join(f'#define {d}\n' for d in defines)+''.join((H/s).read_text()+'\n' for s in sources)
 (D/f'{name}.hip').write_bytes(text.encode())
 print(name,len(text))
