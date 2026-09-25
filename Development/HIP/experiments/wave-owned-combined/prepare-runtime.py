from pathlib import Path
import runpy,shutil,json,hashlib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];OUT=Path('/tmp/wave-owned-runtime')
runpy.run_path(str(HERE/'prepare.py'))
shutil.copytree(ROOT/'src',OUT/'src',dirs_exist_ok=True)
shutil.copytree(Path('/tmp/wave-owned-combined/Development/HIP'),OUT/'Development/HIP',dirs_exist_ok=True)
p=OUT/'Development/HIP/hip_reference_network.h';s=p.read_text()
old='bool w2_frag=std::getenv("W2_FRAG")&&std::string(std::getenv("W2_FRAG"))=="1";'
assert s.count(old)==1
s=s.replace(old,'bool w2_frag=true;')
a='explicit Network(Options o):api(o.runtime),opt(std::move(o)),W(opt.width),H(opt.height){'
assert s.count(a)==1
s=s.replace(a,a+'''const char*enabled=std::getenv("DLSS5_HIP_WAVE_OWNED");if(enabled&&strcmp(enabled,"0")&&strcmp(enabled,"1"))throw std::runtime_error("wave-owned flag");bool use=enabled&&!strcmp(enabled,"1");w2_mode=use?7:0;cw_mode=use?1:0;''')
a='~Network(){api.hipStreamSynchronize(stream);';assert s.count(a)==1
s=s.replace(a,a+'std::printf("WAVE_OWNED_RUNTIME calls=%u replaced=%u enabled=%u\\n",W2Calls(),W2Replaced(),cw_mode);')
p.write_text(s)
shutil.copyfile(ROOT/'Development/HIP/benchmark_vit_reuse.cpp',OUT/'benchmark.cpp')
(OUT/'runtime-manifest.json').write_text(json.dumps({'generated_host_sha256':hashlib.sha256(s.encode()).hexdigest(),'benchmark_sha256':hashlib.sha256((OUT/'benchmark.cpp').read_bytes()).hexdigest(),'native_frame_sha256':hashlib.sha256((ROOT/'src/native_game_frame.h').read_bytes()).hexdigest()},indent=2)+'\n')
print(OUT)
