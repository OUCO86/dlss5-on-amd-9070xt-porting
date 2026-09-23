# mh_fast VGPR cap: the 512-thread ffn_fused kernels allocate 96..109 VGPRs, which lets 12 waves per SIMD reside (3 groups
# of 16 waves per WGP; launch-occupancy-20260923 HW_ID count). 16-wave groups need multiples of 4 waves/SIMD, so the
# next step is 16 waves/SIMD = 4 groups/WGP, which requires <=96 VGPRs. amdgpu_waves_per_eu(16,16) asks the compiler for
# that (spilling if it must; spills change no arithmetic -> bit-exact either way). Module-set host (fence-scope-all):
#   pair1: cap on the mh_ffn_fused_* kernels only      pair2: cap on every 512-thread kernel of mh_fast      pair3 = pair1
from pathlib import Path
import re, shutil
here=Path(__file__).resolve().parent; root=here.parents[3]; out=Path('/tmp/mhfast-vgpr-cap')
for sub in ('pair1','pair2','pair3'): shutil.rmtree(out/sub, ignore_errors=True); (out/sub).mkdir(parents=True)
s0=(root/'hip/multihead_fast_padded.hip').read_text()
OCC='__attribute__((amdgpu_waves_per_eu(16,16))) '
for mode in (1,2,3):
    n=0
    def rep(m):
        global n
        name=m.group(2)
        if m.group(1) and (mode==2 or name.startswith('mh_ffn_fused_')): n+=1; return m.group(0).replace('void '+name+'(',OCC+'void '+name+'(',1)
        return m.group(0)
    s=re.sub(r'(KERNEL __attribute__\(\(amdgpu_flat_work_group_size\(512,512\)\)\) )void (\w+)\(',rep,s0)
    (out/f'pair{mode}'/'multihead-fast-padded-wave-packed.generated.hip').write_text('#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_FFN_HOIST_RES 2\n'+s+'\n')
    print(f'pair{mode}: {n} kernels capped')
