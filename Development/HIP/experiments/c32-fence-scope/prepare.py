# C32 fence scope experiment: same fused body, only the workgroup barrier/fence flavour changes.
# Variants are exported with _pairN suffixes so the existing c32-pair-encode network.exe host
# (SetPairMode appends "_pair<mode>" to every c32_fused_ffn kernel name) runs them unchanged.
#   _pair1: fences restricted to the LDS address space ("local"), WGP mode unchanged
#   _pair2: original workgroup fences, kernel compiled in CU mode (target("cumode"))
#   _pair3: local fences + CU mode
from pathlib import Path
import shutil, re

here = Path(__file__).resolve().parent
root = here.parents[3]
out = Path('/tmp/c32-fence-scope')
out.mkdir(exist_ok=True)
s = (root/'hip/c32_fused_ffn_attention.hip').read_text()
a = s.index('template<bool HalfOutput,bool Mapped=false')
b = s.index('\nKERNEL ', a)
body = s[a:b]
assert body.count('sync_window()') > 0 and body.count('sync_owned_rows()') > 0
helpers = '''
// _pair1/_pair3: order only LDS across the workgroup; no vector-L0 invalidate is required for LDS visibility.
DEV void sync_window_local(){__builtin_amdgcn_fence(3,"workgroup","local");__builtin_amdgcn_s_barrier();__builtin_amdgcn_fence(2,"workgroup","local");}
DEV void sync_owned_rows_local(){
#if HIP_C32_LOCAL_QKV_SYNC
 __builtin_amdgcn_fence(3,"workgroup","local");__builtin_amdgcn_fence(2,"workgroup","local");
#else
 sync_window_local();
#endif
}
'''
code = '#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n' + s + '\n' + helpers
names = re.findall(r'^void (c32_\w+)\(', s[b:], re.M)
modes = {1: ('local', ''), 2: ('orig', '__attribute__((target("cumode"))) '), 3: ('local', '__attribute__((target("cumode"))) ')}
for mode, (fence, attr) in modes.items():
    variant = body.replace('c32_fused_body(', f'c32_fence{mode}_body(', 1)
    if fence == 'local':
        variant = variant.replace('sync_window()', 'sync_window_local()').replace('sync_owned_rows()', 'sync_owned_rows_local()')
    code += '\n' + variant + '\n'
    for name in names:
        line = next(x for x in s[b:].splitlines() if x.startswith('void '+name+'('))
        code += f'KERNEL __attribute__((amdgpu_flat_work_group_size(128,128))) {attr}C32_OCC\n'
        code += line.replace('void '+name+'(', f'void {name}_pair{mode}(', 1).replace('c32_fused_body<', f'c32_fence{mode}_body<')+'\n'
(out/'kernel.hip').write_text(code)
print('kernels', len(names), 'variants', list(modes))
