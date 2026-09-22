# CU mode by workgroup size. Baseline = fence-modules (LDS fences everywhere, C32 in CU mode).
# pair1: CU mode also on 128-thread kernels of mh_fused/mh_fast/deep_fast
# pair2: CU mode on 128- and 256-thread kernels
# pair3: CU mode on single-wave (32-thread) kernels only
# Uses the fence-scope-all host (routes c32_fused_ffn/mh_fused/deep_fast/mh_fast to modules/pair<n>).
from pathlib import Path
import re, shutil
here=Path(__file__).resolve().parent; root=here.parents[3]; out=Path('/tmp/fence-cu-size')
for sub in ('pair1','pair2','pair3'): shutil.rmtree(out/sub, ignore_errors=True); (out/sub).mkdir(parents=True)
MODULES=[('multihead_fused_attention',['HIP_MH_RTZ_ISA 1'],'multihead_fused_attention.hip'),
 ('deep_fast-packed',['HIP_PREPACKED_WEIGHTS 1','HIP_BRANCHLESS_F 1'],'deep_fast.hip'),
 ('multihead-fast-padded-wave-packed',['HIP_PREPACKED_WEIGHTS 1','HIP_FFN_HOIST_RES 2'],'multihead_fast_padded.hip')]
CU='__attribute__((target("cumode"))) '
SETS={1:{'128'},2:{'128','256'},3:{'32'}}
for mode,sizes in SETS.items():
    for name,defs,src in MODULES:
        s=(root/'hip'/src).read_text(); n=0
        def rep(m):
            global n
            if m.group(2) in sizes: n+=1; return m.group(1)+CU
            return m.group(0)
        s=re.sub(r'(KERNEL\s*__attribute__\(\(amdgpu_flat_work_group_size\((\d+),\d+\)\)\)\s*)',rep,s)
        if '32' in sizes and '#define WAVE KERNEL __attribute__((amdgpu_flat_work_group_size(32,32)))' in s:
            s=s.replace('#define WAVE KERNEL __attribute__((amdgpu_flat_work_group_size(32,32)))','#define WAVE KERNEL __attribute__((amdgpu_flat_work_group_size(32,32))) '+CU); n+=s.count('\nWAVE ')
        (out/f'pair{mode}'/f'{name}.generated.hip').write_text('#define HIP_ISA_HALF 1\n'+''.join(f'#define {d}\n' for d in defs)+s+'\n')
        print(f'pair{mode} {name}: {n} kernels/decls marked cumode')
