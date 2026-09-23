# Ablation upper bounds for the ffn_fused tail (43% of the kernel per mhfast-phase-trace): NOT bit-exact, timing only.
# The host is patched to record bitdiff instead of throwing. Same module-set host as mhfast-vgpr-cap.
#   pair1: the 32-iteration serial sum-of-squares becomes a single square (cost of the serial loop)
#   pair2: no storage.raw round trip, no two barriers, inv = 1 (cost of the normalisation exchange)
#   pair3: the 24 norm byte stores are never executed (data-dependent impossible branch keeps the QKV WMMAs)
from pathlib import Path
import shutil
here=Path(__file__).resolve().parent; root=here.parents[3]; out=Path('/tmp/mhfast-tail-ablate')
for sub in ('pair1','pair2','pair3'): shutil.rmtree(out/sub, ignore_errors=True); (out/sub).mkdir(parents=True)
s0=(root/'hip/multihead_fast_padded.hip').read_text()
loop='float ss=0;for(uint k=0;k<32;k++){float v=storage.raw[(head*16+row)*33+k];ss+=v*v;}'
import re
mb=re.search(r"\n *if\(part<2\)\{for\(uint e=0;e<8;e\+\+\)storage\.raw\[\(\(wave/2\).*?__builtin_amdgcn_s_barrier\(\);\n *\}\n",s0,re.S)
assert mb and mb.group(0).count('s_barrier')==2 and 'inverse[tid]' in mb.group(0); block=mb.group(0)
use='float inv=part<2?inverse[(wave/2)*16+row]:1.f;norm[((first+row)*3+part)*C+wave*16+rc]=static_cast<unsigned char>(q8_fused_round(q[e]*inv));'
for o in (loop,block,use): assert s0.count(o)==1,(o[:50],s0.count(o))
V={1:s0.replace(loop,'float v=storage.raw[(head*16+row)*33];float ss=v*v;'),
   2:s0.replace(block,'\n').replace(use,'float inv=1.f;norm[((first+row)*3+part)*C+wave*16+rc]=static_cast<unsigned char>(q8_fused_round(q[e]*inv));'),
   3:s0.replace(use,'float inv=part<2?inverse[(wave/2)*16+row]:1.f;if(q[e]*inv==12345.f)norm[((first+row)*3+part)*C+wave*16+rc]=1;')}
for m,s in V.items():
    (out/f'pair{m}'/'multihead-fast-padded-wave-packed.generated.hip').write_text('#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_FFN_HOIST_RES 2\n'+s+'\n')
print('written')
