# C32 transposed tail (HIP_C32_TRANSPOSED_TAIL): kernel-suffix ABBA host (reuses c32-lds-alias/network.exe, which runs every C32
# kernel against its _pair1/_pair2/_pair3 twins in interleaved order and checks the whole-network output bit-exactly).
# Output /tmp/c32-transposed-tail/: kernel.hip (production body + three transposed twins), prod.hip (production only, for the
# ISA-unchanged check against prod6).
from pathlib import Path
import re
here=Path(__file__).resolve().parent; root=here.parents[3]; out=Path('/tmp/c32-transposed-tail'); out.mkdir(exist_ok=True)
s=(root/'hip/c32_fused_ffn_attention.hip').read_text()
prefix='#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_C32_DIAG_WEIGHTS 1\n'
(out/'prod.hip').write_text(prefix+s+'\n')
a=s.index('template<bool HalfOutput,bool Mapped=false'); b=s.index('\nKERNEL ',a); body=s[a:b]
assert body.count('HIP_C32_TRANSPOSED_TAIL')>=5, body.count('HIP_C32_TRANSPOSED_TAIL')
# the twin body sees the flag as 1 (the file-level macro C32_WMMA_ACC must also swap: give the twin its own macro)
v=body.replace('HIP_C32_TRANSPOSED_TAIL','1').replace('C32_WMMA_ACC(','C32_WMMA_ACC_T(')
code=prefix+s+'\n#define C32_WMMA_ACC_T(a,b,c) __builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(b,a,c)\n'
names=re.findall(r'^void (c32_\w+)\(',s[b:],re.M)
for mode in (1,2,3):
    code+='\n'+v.replace('c32_fused_body(',f'c32_tt{mode}_body(',1)+'\n'
    for name in names:
        line=next(x for x in s[b:].splitlines() if x.startswith('void '+name+'('))
        code+='KERNEL __attribute__((amdgpu_flat_work_group_size(128,128))) C32_OCC\n'+line.replace('void '+name+'(',f'void {name}_pair{mode}(',1).replace('c32_fused_body<',f'c32_tt{mode}_body<')+'\n'
(out/'kernel.hip').write_text(code); print('kernels',len(names))
