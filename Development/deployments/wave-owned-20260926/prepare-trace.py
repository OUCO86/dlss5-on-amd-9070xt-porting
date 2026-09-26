"""Instrument the actual production host for replacement-count regression only."""
from pathlib import Path
import shutil,json,hashlib
ROOT=Path(__file__).resolve().parents[3];OUT=Path('/tmp/wave-owned-production/trace')
shutil.copytree(ROOT/'src',OUT/'src',dirs_exist_ok=True);(OUT/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (ROOT/'Development/HIP').glob('*.h'):shutil.copyfile(p,OUT/'Development/HIP'/p.name)
p=OUT/'Development/HIP/hip_reference_network.h';s=p.read_text();original=s
s=s.replace('class Network {','class Network {\n unsigned trace_calls=0,trace_replaced=0;',1)
a='  static const std::set<std::string> accelerated=';assert s.count(a)==1
s=s.replace(a,'''  static const std::set<std::string> trace_c32={"c32_fast_ffn_attention_fused_half_chain","c32_fast_ffn_attention_fused_half_mapped","c32_fast_ffn_attention_fused_half_chain_finish","c32_fast_ffn_attention_fused_half_chain_finish_dcrop","c32_post_merge_head_half","c32_fast_ffn_attention_fused_half_prefix_finish_main8"};
  if(module=="c32_wave1"||module=="c64_wave2"){++trace_calls;++trace_replaced;}else if(trace_c32.count(kernel)||(module=="mh_fused"&&(kernel.rfind("c64_attention_project",0)==0||kernel.rfind("c128_attention_project",0)==0||kernel.rfind("c256_attention_project",0)==0)))++trace_calls;
'''+a)
a='~Network(){api.hipStreamSynchronize(stream);';assert s.count(a)==1
s=s.replace(a,a+'std::printf("WAVE_OWNED_RUNTIME calls=%u replaced=%u enabled=%u\\n",trace_calls,trace_replaced,unsigned(WaveOwnedActive()));');p.write_text(s)
shutil.copyfile(ROOT/'Development/HIP/benchmark_vit_reuse.cpp',OUT/'benchmark.cpp')
(OUT.parent/'trace-manifest.json').write_text(json.dumps({'production_host_sha256':hashlib.sha256(original.encode()).hexdigest(),'traced_host_sha256':hashlib.sha256(s.encode()).hexdigest()},indent=2)+'\n')
print(OUT)
