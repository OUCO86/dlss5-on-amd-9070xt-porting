"""m32-sweep: census of 16-token-per-wave kernels on the current production (prod8 + wave-owned + C512_M32, PDL off for the
census because duplicating a *_pdl kernel double-counts its flags). Writes /tmp/m32-sweep:
  network.cpp  production host copy + SetDup()/DupHits() + SetCand() candidate hook
  survey mode: env SWEEP_TARGETS="name$,prefix,..."; each target ABBA (no dup / dup x2), marginal = B - A.
  candidate mode: env SWEEP_CANDS="1,2,..."; each candidate ABBA (production / candidate), bit-checked + dynamic history.
Candidate kernels (if any) are appended to deep_fast.hip / multihead_fast_padded.hip copies from cand_*.inc next to this file."""
from pathlib import Path
import hashlib,json,shutil,re
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];OUT=Path('/tmp/m32-sweep');OUT.mkdir(exist_ok=True)
def rep(s,a,b,count=1):
 assert s.count(a)==count,(a[:120],s.count(a))
 return s.replace(a,b)
(OUT/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (ROOT/'Development/HIP').glob('*.h'):shutil.copyfile(p,OUT/'Development/HIP'/p.name)
p=OUT/'Development/HIP/hip_reference_network.h';s=p.read_text()
s=rep(s,'class Network {','class Network {\n public: unsigned dup_hits=0,cand=0,cand_hits=0; private:')
s=rep(s,' Handle Stream()const{return stream;}',''' void SetDup(const std::string&prefix){Synchronize();opt.dup_prefix=prefix;dup_hits=0;}
 void SetCand(unsigned c){Synchronize();cand=c;cand_hits=0;}
 Handle Stream()const{return stream;}''')
s=rep(s,'?opt.dup_count:1u);','?opt.dup_count:1u);if(repeats_here>launch_repeats)++dup_hits;')
# Candidate hook: kernel-name remap inside Run (after all module/kernel resolution, before launch). CAND_REMAP is filled by
# cand_*.py snippets (none yet -> identity).
remap=(HERE/'cand_remap.inc').read_text() if (HERE/'cand_remap.inc').exists() else ''
s=rep(s,'  if(opt.wall_profile)api.Check(api.hipStreamSynchronize(stream),"wall profile drain");','  '+remap+'\n  if(opt.wall_profile)api.Check(api.hipStreamSynchronize(stream),"wall profile drain");')
p.write_text(s)
for src,inc,dst in (('hip/deep_fast.hip','cand_deep.inc','deep.hip'),('hip/multihead_fast_padded.hip','cand_mh.inc','mh.hip')):
 if (HERE/inc).exists():
  prefix=('#define HIP_FFN_LINE_STORES 1\n' if 'deep' not in src else '')+'#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n'+('#define HIP_BRANCHLESS_F 1\n' if 'deep' in src else '#define HIP_FFN_HOIST_RES 2\n')
  (OUT/dst).write_text(prefix+(ROOT/src).read_text()+'\n'+(HERE/inc).read_text())
native=(ROOT/'src/native_hip_network.h').read_text();a=native.index('hip_reference::Options o;');b=native.index('  const wchar_t*modules=',a)
options=native[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift','o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)','o.assets=argv[1]')
assert 'o.width=W' in options and 'o.assets=argv[1]' in options
(OUT/'network.cpp').write_text((HERE/'runner.cpp.in').read_text().replace('/* OPTIONS */',options))
for name in ('build.ps1','run.ps1'):
 if (HERE/name).exists():shutil.copyfile(HERE/name,OUT/name)
(OUT/'manifest.json').write_text(json.dumps({'host_source_sha256':hashlib.sha256((ROOT/'Development/HIP/hip_reference_network.h').read_bytes()).hexdigest()},indent=2)+'\n')
print(OUT)
