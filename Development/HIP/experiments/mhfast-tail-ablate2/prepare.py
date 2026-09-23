# Ablation upper bounds on top of the transposed tail (HIP_FFN_TRANSPOSED_TAIL=1 in production): what is left for a
# non-bit-exact normalisation rewrite. Timing only, outputs broken (tolerant host).
#   pair1: whole normalisation exchange removed (storage.raw write, 2 barriers, serial loop, inverse read; inv = 1)
#   pair2: serial 32-term loop -> one square (exchange kept)      pair3 = pair1
from pathlib import Path
import re, shutil
here=Path(__file__).resolve().parent; root=here.parents[3]; out=Path('/tmp/mhfast-tail-ablate2')
for sub in ('pair1','pair2','pair3'): shutil.rmtree(out/sub, ignore_errors=True); (out/sub).mkdir(parents=True)
s0=(root/'hip/multihead_fast_padded.hip').read_text()
assert '#define HIP_FFN_TRANSPOSED_TAIL 1' in s0
# the storage.raw write is wrapped in #if HIP_FFN_TRANSPOSED_TAIL/#else/#endif; remove the whole balanced span through the 2nd barrier
mb=re.search(r"#if HIP_FFN_TRANSPOSED_TAIL\n *if\(part<2\)\{for\(uint e=0;e<8;e\+\+\)storage\.raw\[\(\(wave/2\)\*16\+rc\)\*33.*?#endif\n.*?__builtin_amdgcn_s_barrier\(\);\n *\}\n",s0,re.S)
assert mb and mb.group(0).count('s_barrier')==2 and 'inverse[tid]' in mb.group(0) and mb.group(0).count('#if')==1 and mb.group(0).count('#endif')==1; block=mb.group(0)
use='   {float inv=part<2?inverse[(wave/2)*16+rc]:1.f;for(uint e=0;e<8;e++)norm[((first+rc)*3+part)*C+wave*16+group*8+e]=static_cast<unsigned char>(q8_fused_round(q[e]*inv));}\n'
loop='float ss=0;for(uint k=0;k<32;k++){float v=storage.raw[(head*16+row)*33+k];ss+=v*v;}'
assert s0.count(use)==1 and s0.count(loop)==1
p1=s0.replace(block,'\n',1).replace(use,use.replace('part<2?inverse[(wave/2)*16+rc]:1.f','1.f'),1)
p2=s0.replace(loop,'float v=storage.raw[(head*16+row)*33];float ss=v*v;',1)
for m,s in {1:p1,2:p2,3:p1}.items():
    (out/f'pair{m}'/'multihead-fast-padded-wave-packed.generated.hip').write_text('#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_FFN_HOIST_RES 2\n'+s+'\n')
print('written')
