from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[4];out=Path('/tmp/kernel-bottleneck');out.mkdir(exist_ok=True)
shutil.copytree(root/'src',out/'src',dirs_exist_ok=True);(out/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (root/'Development/HIP').glob('*.h'):shutil.copyfile(p,out/'Development/HIP'/p.name)
shutil.copyfile(root/'Development/HIP/benchmark_live_capture.cpp',out/'Development/HIP/benchmark.cpp')
p=out/'Development/HIP/hip_reference_network.h';s=p.read_text().replace('class Network {','class Network {\n bool counter_repeat_done=false;size_t counter_launch_index=0;',1)
needle='for(unsigned repeat=0;repeat<repeats_here;repeat++)api.Check('
assert s.count(needle)==1
s=s.replace(needle,'''++counter_launch_index;if(!counter_repeat_done){if(const char*target=std::getenv("DLSS5_COUNTER_TARGET");target&&kernel==target){counter_repeat_done=true;repeats_here=10000;fprintf(stdout,"COUNTER_TARGET name=%s normal_launch_index=%zu repeats=%u\\n",kernel.c_str(),counter_launch_index,repeats_here);}}
 for(unsigned repeat=0;repeat<repeats_here;repeat++)api.Check(''',1)
p.write_text(s)
