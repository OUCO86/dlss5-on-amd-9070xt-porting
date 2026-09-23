# mh_fast line stores (HIP_FFN_LINE_STORES): module-set ABBA host (fence-scope-all network.exe, bit-exact enforced), three identical
# twins pair1..3 = three replications; prod.hip = flag 0 for the ISA-unchanged check against prod6.
from pathlib import Path
import shutil
here=Path(__file__).resolve().parent; root=here.parents[3]; out=Path('/tmp/mhfast-line-stores')
for sub in ('pair1','pair2','pair3'): shutil.rmtree(out/sub, ignore_errors=True); (out/sub).mkdir(parents=True)
s0=(root/'hip/multihead_fast_padded.hip').read_text()
prefix='#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_FFN_HOIST_RES 2\n'
(out/'prod.hip').write_text(prefix+s0+'\n')
assert s0.count('#define HIP_FFN_LINE_STORES 0')==1
s=s0.replace('#define HIP_FFN_LINE_STORES 0','#define HIP_FFN_LINE_STORES 1',1)
for mode in (1,2,3): (out/f'pair{mode}'/'multihead-fast-padded-wave-packed.generated.hip').write_text(prefix+s+'\n')
print('written')
