from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent;out=Path('/tmp/network-timeline');out.mkdir(exist_ok=True)
shutil.copytree(root/'src',out/'src',dirs_exist_ok=True);(out/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (root/'Development/HIP').glob('*.h'):shutil.copyfile(p,out/'Development/HIP'/p.name)
p=out/'Development/HIP/hip_reference_network.h';s=p.read_text().replace('class Network {','class Network {\n'+(here/'trace-members.inc').read_text(),1)
needle='for(unsigned repeat=0;repeat<repeats_here;repeat++)api.Check(';assert s.count(needle)==1
before='''size_t probe_index=probe_cursor;
 if(probe_active){if(probe_cursor>=probe_records.size())throw std::runtime_error("probe capacity");auto&r=probe_records[probe_cursor++];r.module=module;r.kernel=kernel;r.stage.clear();r.args.clear();r.groups=groups?groups:unsigned((count+255ull)/256);r.threads=threads;r.count=count;r.frame=probe_frame;
 auto append=[&](auto x){if(!r.args.empty())r.args+=';';if constexpr(std::is_integral_v<decltype(x)>)r.args+=std::to_string((unsigned long long)x);else r.args+='_';};(append(args),...);
 api.Check(api.hipEventRecord(r.begin,stream),"probe kernel begin");}
 '''
s=s.replace(needle,before+needle,1)
needle='if(opt.profile)api.Check(api.hipEventRecord(timing.end,stream),"event end");';assert s.count(needle)==1
s=s.replace(needle,'if(probe_active)api.Check(api.hipEventRecord(probe_records[probe_index].end,stream),"probe kernel end");'+needle,1)
needle='void Stage(const std::string&name,const Tensor&t){';assert s.count(needle)==1
s=s.replace(needle,needle+'if(probe_active){for(size_t i=probe_mark;i<probe_cursor;i++)probe_records[i].stage=name;probe_mark=probe_cursor;}',1)
needle=' Handle Stream()const{return stream;}';assert s.count(needle)==1
s=s.replace(needle,(here/'trace-public.inc').read_text()+needle,1);p.write_text(s)
# Capture the exact current encoded input and raw expected output, without a profiler.
s=(root/'Development/HIP/benchmark_live_capture.cpp').read_text();needle=';void*local_in=nullptr,*local_out=nullptr;';assert s.count(needle)==1
s=s.replace(needle,';std::ofstream("input.f32",std::ios::binary).write(reinterpret_cast<char*>(encoded.data()),encoded.size()*4);std::ofstream("expected.f32",std::ios::binary).write(reinterpret_cast<char*>(expected.data()),expected.size()*4);void*local_in=nullptr,*local_out=nullptr;',1)
(out/'dump.cpp').write_text(s.replace('#include "../../src/','#include "'+str(root/'src')+'/'))
s=(root/'src/native_hip_network.h').read_text();a=s.index('hip_reference::Options o;');b=s.index('  const wchar_t*modules=',a)
opts=s[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift','o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)','o.assets=argv[1]')
code=(here/'runner.cpp.in').read_text().replace('/* OPTIONS */',opts)
(out/'pure.cpp').write_text(code)
