# C32 LDS: the NeedIn16 kernels (half_mapped, post_merge_head, post_merge_fused) carry a 4352-byte f16 copy of the staged
# input (in16) next to the 8448-byte Scratch union and the 6912-byte packed rows: 19712 B/group -> 3 groups per CU in
# CU mode (64 KB), measured 6 waves/SIMD; the other C32 kernels (15360 B) get 4 groups/CU, 8 waves/SIMD
# (launch-occupancy-20260923). in16 is written in staging and last read by the residual initialisation before the FFN;
# Scratch is first written in the QKV normalisation, after two sync_windows. Aliasing in16 onto Scratch keeps every
# value and address pattern within each region identical -> bit-exact, LDS 15360 for all ten kernels.
# Three identical _pairN sets = three replications in the kernel-suffix ABBA host.
from pathlib import Path
import re
here=Path(__file__).resolve().parent; root=here.parents[3]; out=Path('/tmp/c32-lds-alias'); out.mkdir(exist_ok=True)
s=(root/'hip/c32_fused_ffn_attention.hip').read_text()
a=s.index('template<bool HalfOutput,bool Mapped=false'); b=s.index('\nKERNEL ',a); body=s[a:b]
old=' __attribute__((shared)) _Float16 in16[NeedIn16?64*34:1];\n'
new=' _Float16*in16=reinterpret_cast<_Float16*>(scratch.ex); // aliased: in16 dies at the residual init, scratch is born in QKV (two sync_windows later)\n'
assert body.count(old)==1
assert 'HIP_C32_FOLDED_FFN 1' in s and 'HIP_C32_REGISTER_FFN 1' in s  # scratch.hidden path (would be live during the FFN) must be compiled out
v=body.replace(old,new,1)
code='#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_C32_DIAG_WEIGHTS 1\n'+s+'\n'
names=re.findall(r'^void (c32_\w+)\(',s[b:],re.M)
for mode in (1,2,3):
    code+='\n'+v.replace('c32_fused_body(',f'c32_alias{mode}_body(',1)+'\n'
    for name in names:
        line=next(x for x in s[b:].splitlines() if x.startswith('void '+name+'('))
        code+='KERNEL __attribute__((amdgpu_flat_work_group_size(128,128))) C32_OCC\n'+line.replace('void '+name+'(',f'void {name}_pair{mode}(',1).replace('c32_fused_body<',f'c32_alias{mode}_body<')+'\n'
(out/'kernel.hip').write_text(code); print('kernels',len(names))
