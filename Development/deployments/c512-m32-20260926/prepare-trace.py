"""Diagnostic copy of the production host that counts C512 chain dispatches (mix + QKV per C512 block) and how many went
to the 32-token modules; prints C512_M32_RUNTIME at destruction. Correctness regression only; timing uses the unmodified host."""
from pathlib import Path
import shutil,json,hashlib
ROOT=Path(__file__).resolve().parents[3];OUT=Path('/tmp/c512-m32-production/trace')
shutil.copytree(ROOT/'src',OUT/'src',dirs_exist_ok=True);(OUT/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (ROOT/'Development/HIP').glob('*.h'):shutil.copyfile(p,OUT/'Development/HIP'/p.name)
p=OUT/'Development/HIP/hip_reference_network.h';s=p.read_text();original=s
s=s.replace('class Network {','class Network {\n unsigned c5_trace_calls=0,c5_trace_replaced=0;',1)
a='  static const std::set<std::string> accelerated=';assert s.count(a)==1
s=s.replace(a,'''  if(module=="c512_m32_mh"||module=="c512_m32_deep"){++c5_trace_calls;++c5_trace_replaced;}else if(kernel=="split_mix_blocked_h16w"||kernel=="mh_qkv_normalize_frag_c512")++c5_trace_calls;
'''+a)
a='~Network(){api.hipStreamSynchronize(stream);';assert s.count(a)==1
s=s.replace(a,a+'std::printf("C512_M32_RUNTIME calls=%u replaced=%u enabled=%u\\n",c5_trace_calls,c5_trace_replaced,unsigned(C512M32Active()));');p.write_text(s)
shutil.copyfile(ROOT/'Development/HIP/benchmark_vit_reuse.cpp',OUT/'benchmark.cpp')
(OUT.parent/'trace-manifest.json').write_text(json.dumps({'production_host_sha256':hashlib.sha256(original.encode()).hexdigest(),'traced_host_sha256':hashlib.sha256(s.encode()).hexdigest()},indent=2)+'\n')
print(OUT)
