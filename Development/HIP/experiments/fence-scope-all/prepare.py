# Network-wide fence scope experiment. Builds alternate module SETS instead of renaming kernels:
#   modules/         production selected-modules (baseline)
#   modules/pair1/   same four sources, every workgroup fence restricted to the LDS address space ("local")
#   modules/pair2/   pair1 + KERNEL macro adds target("cumode") (workgroup confined to one CU)
# pair3 = C32 module from pair2 (CU mode) + the other three from pair1 (local fences only); assembled on the box by copying.
# The host loads the four affected modules from each set under "<module>_pair<n>" and, per timing slot,
# routes launches of mh_fused / mh_fast / deep_fast / c32_fused_ffn to the selected set. Barriers, math,
# layouts untouched. Outputs must stay bit-exact.
from pathlib import Path
import shutil, re

here = Path(__file__).resolve().parent
root = here.parents[3]
out = Path('/tmp/fence-scope-all')
out.mkdir(exist_ok=True)
for sub in ('pair1','pair2','Development'):shutil.rmtree(out/sub, ignore_errors=True)

# (host module key, hsaco file name, extra defines, source) — mirrors hip/build-modules.ps1 rows
MODULES = [
    ('c32_fused_ffn', 'c32_fused_ffn_attention-packed', ['HIP_PREPACKED_WEIGHTS 1', 'HIP_C32_DIAG_WEIGHTS 1'], 'c32_fused_ffn_attention.hip'),
    ('mh_fused', 'multihead_fused_attention', ['HIP_MH_RTZ_ISA 1'], 'multihead_fused_attention.hip'),
    ('deep_fast', 'deep_fast-packed', ['HIP_PREPACKED_WEIGHTS 1', 'HIP_BRANCHLESS_F 1'], 'deep_fast.hip'),
    ('mh_fast', 'multihead-fast-padded-wave-packed', ['HIP_PREPACKED_WEIGHTS 1', 'HIP_FFN_HOIST_RES 2'], 'multihead_fast_padded.hip'),
]
KERNEL_DEF = '#define KERNEL extern "C" __attribute__((global))'
stats = []
for mode in (1, 2):
    d = out/f'pair{mode}'; d.mkdir()
    for key, name, defines, src in MODULES:
        s = (root/'hip'/src).read_text()
        n_fence = len(re.findall(r'__builtin_amdgcn_fence\([23],"workgroup"\)', s))
        s2 = re.sub(r'__builtin_amdgcn_fence\(([23]),"workgroup"\)', r'__builtin_amdgcn_fence(\1,"workgroup","local")', s)
        assert s2.count(KERNEL_DEF) == 1, src
        if mode == 2:
            s2 = s2.replace(KERNEL_DEF, '#define KERNEL extern "C" __attribute__((global)) __attribute__((target("cumode")))')
        text = '#define HIP_ISA_HALF 1\n' + ''.join(f'#define {x}\n' for x in defines) + s2 + '\n'
        (d/f'{name}.generated.hip').write_text(text)
        stats.append((mode, name, n_fence))
for mode, name, n in stats: print(f'pair{mode} {name}: {n} workgroup fences rewritten')

# host
(out/'Development/HIP').mkdir(parents=True)
for p in (root/'Development/HIP').glob('*.h'):
    shutil.copyfile(p, out/'Development/HIP'/p.name)
p = out/'Development/HIP/hip_reference_network.h'
s = p.read_text()
s = s.replace('class Network {', 'class Network {\n unsigned pair_mode=0,pair_calls=0;\n static bool PairModule(const std::string&m){return m=="c32_fused_ffn"||m=="mh_fused"||m=="deep_fast"||m=="mh_fast";}\n std::string Route(const std::string&m){if(pair_mode&&PairModule(m)){++pair_calls;return m+"_pair"+std::to_string(pair_mode);}return m;}\n', 1)
old = 'api.hipModuleLaunchKernel(Fn(module,kernel),'
assert s.count(old) == 1
s = s.replace(old, 'api.hipModuleLaunchKernel(Fn(Route(module),kernel),', 1)
anchor = 'modules["mh_fast"]=m;}'
assert s.count(anchor) == 1
load = anchor + '''
for(unsigned pm=1;pm<=3;pm++){const char*pf[][2]={{"c32_fused_ffn","c32_fused_ffn_attention-packed.hsaco"},{"mh_fused","multihead_fused_attention.hsaco"},{"deep_fast","deep_fast-packed.hsaco"},{"mh_fast","multihead-fast-padded-wave-packed.hsaco"}};for(auto&v:pf){Handle m{};api.Check(api.LoadModule(&m,(opt.modules+"/pair"+std::to_string(pm)+"/"+v[1]).c_str()),v[1]);modules[std::string(v[0])+"_pair"+std::to_string(pm)]=m;}}'''
s = s.replace(anchor, load, 1)
s = s.replace(' Handle Stream()const{return stream;}', ' void SetPairMode(unsigned m){pair_mode=m;pair_calls=0;} unsigned PairCalls()const{return pair_calls;}\n Handle Stream()const{return stream;}', 1)
assert 'SetPairMode' in s
p.write_text(s)
x = (root/'src/native_hip_network.h').read_text(); a = x.index('hip_reference::Options o;'); b = x.index('  const wchar_t*modules=', a)
opts = x[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift', 'o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)', 'o.assets=argv[1]')
r = (root/'Development/HIP/experiments/vit-schedule-cause/runner.cpp.in').read_text()
a = r.index(' for(unsigned frame=0;'); b = r.index('api.hipFree(x);', a)
r = r[:a] + (here/'timing.inc').read_text() + r[b:]
(out/'network.cpp').write_text(r.replace('/* OPTIONS */', opts).replace('PASS ViT schedule controls', 'PASS fence scope all'))
print('host written', out/'network.cpp')
