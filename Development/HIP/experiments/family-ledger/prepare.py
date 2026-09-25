# Builds /tmp/family-ledger/ledger.cpp: production HIP network + sparse prefix markers with dynamic topology (wave-owned aware).
from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent;out=Path('/tmp/family-ledger');(out/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (root/'Development/HIP').glob('*.h'):shutil.copyfile(p,out/'Development/HIP'/p.name)
for p in (root/'Development/HIP').glob('*.inc'):shutil.copyfile(p,out/'Development/HIP'/p.name)
p=out/'Development/HIP/hip_reference_network.h';s=p.read_text().replace('class Network {','class Network {\n'+(here/'members.inc').read_text(),1)
needle='if(opt.profile)api.Check(api.hipEventRecord(timing.end,stream),"event end");';assert s.count(needle)==1
s=s.replace(needle,'if(topo_active){topo_kernels.push_back(module+":"+kernel);++prefix_cursor;}else if(prefix_active){++prefix_cursor;if(prefix_cursor==prefix_total)api.Check(api.hipEventRecord(prefix_end,stream),"compute end marker");else if(prefix_cursor==prefix_cut)api.Check(api.hipEventRecord(prefix_mid,stream),"cut marker");}'+needle,1)
needle='void Stage(const std::string&name,const Tensor&t){';assert s.count(needle)==1
s=s.replace(needle,needle+'if(topo_active)topo_stages.emplace_back(name,prefix_cursor);',1)
needle=' Handle Stream()const{return stream;}';assert s.count(needle)==1
s=s.replace(needle,(here/'public.inc').read_text()+needle,1);p.write_text(s)
x=(root/'src/native_hip_network.h').read_text();a=x.index('hip_reference::Options o;');b=x.index('  const wchar_t*modules=',a)
opts=x[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift','o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)','o.assets=argv[1]')
assert 'o.width=W' in opts and 'o.assets=argv[1]' in opts
(out/'ledger.cpp').write_text((here/'runner.cpp.in').read_text().replace('/* OPTIONS */',opts))
print('wrote',out/'ledger.cpp')
