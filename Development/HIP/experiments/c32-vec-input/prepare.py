"""c32-vec-input: single-wave C32 candidates as whole-module swaps of c32-wave1 (production recipe + macro):
cand1 CW_VEC_INPUT=1 (mapped/post input rows as b128/b64), cand2 + CW_PREFIX_SPLIT=1, cand3 CW_PREFIX_SPLIT=1 only.
Writes /tmp/cvi: network.cpp (production host + SetCand hook), cvi-*.hip, build/run scripts."""
from pathlib import Path
import hashlib, json, shutil
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[3]; OUT = Path('/tmp/cvi'); OUT.mkdir(exist_ok=True)
def rep(s, a, b):
    assert s.count(a) == 1, (a[:100], s.count(a)); return s.replace(a, b)
(OUT / 'Development/HIP').mkdir(parents=True, exist_ok=True)
for p in (ROOT / 'Development/HIP').glob('*.h'): shutil.copyfile(p, OUT / 'Development/HIP' / p.name)
p = OUT / 'Development/HIP/hip_reference_network.h'; s = p.read_text()
s = rep(s, 'class Network {', 'class Network {\n public: unsigned dup_hits=0,cand=0,cand_hits=0; private:')
s = rep(s, ' Handle Stream()const{return stream;}', ''' void SetDup(const std::string&prefix){Synchronize();opt.dup_prefix=prefix;dup_hits=0;}
 void SetCand(unsigned c){Synchronize();cand=c;cand_hits=0;}
 Handle Stream()const{return stream;}''')
s = rep(s, '?opt.dup_count:1u);', '?opt.dup_count:1u);if(repeats_here>launch_repeats)++dup_hits;')
s = rep(s, '  if(opt.wall_profile)api.Check(api.hipStreamSynchronize(stream),"wall profile drain");',
        '  ' + (HERE / 'cand_remap.inc').read_text() + '\n  if(opt.wall_profile)api.Check(api.hipStreamSynchronize(stream),"wall profile drain");')
p.write_text(s)
base = '#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define CW_ROLL_HIDDEN 1\n#define CW_ROLL_WINDOW 1\n'
body = (ROOT / 'hip/c32_fused_ffn_attention.hip').read_text() + '\n' + (ROOT / 'hip/wave_owned_c32.inc').read_text() + '\n'
man = {}
for name, extra in (('cvi-vec', '#define CW_VEC_INPUT 1\n'), ('cvi-vecsplit', '#define CW_VEC_INPUT 1\n#define CW_PREFIX_SPLIT 1\n'), ('cvi-split', '#define CW_PREFIX_SPLIT 1\n')):
    src = base + extra + body; (OUT / (name + '.hip')).write_text(src); man[name] = hashlib.sha256(src.encode()).hexdigest()
native = (ROOT / 'src/native_hip_network.h').read_text(); a = native.index('hip_reference::Options o;'); b = native.index('  const wchar_t*modules=', a)
options = native[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift', 'o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)', 'o.assets=argv[1]')
assert 'o.width=W' in options and 'o.assets=argv[1]' in options
(OUT / 'network.cpp').write_text((HERE / 'runner.cpp.in').read_text().replace('/* OPTIONS */', options))
for name in ('build.ps1', 'run.ps1'): shutil.copyfile(HERE / name, OUT / name)
man['host_source_sha256'] = hashlib.sha256((ROOT / 'Development/HIP/hip_reference_network.h').read_bytes()).hexdigest()
(OUT / 'manifest.json').write_text(json.dumps(man, indent=2) + '\n'); print(OUT)
