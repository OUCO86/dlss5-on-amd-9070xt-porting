from pathlib import Path
import runpy
h=Path(__file__).resolve().parent;out=Path('/tmp/wmma-groups-gap');runpy.run_path(str(h/'prepare.py'))
s=(out/'kernel.hip').read_text()
for kind,start,end in [('mat','template<uint W,bool MGroup,bool Wide=true', 'template<uint W,bool MGroup> DEV void grouped_load_body'),('load','template<uint W,bool MGroup> DEV void grouped_load_body','\nextern "C" __attribute__((global)) __attribute__((amdgpu_flat_work_group_size(32,32))) void mat_i1')]:
 a=s.index(start);b=s.index(end,a+1);part=s[a:b]
 # Matrix part ends immediately before the load template; load part before first entry.
 part=part.replace('grouped_pair_body','uniform_pair_body').replace('grouped_load_body','uniform_load_body')
 needle='block()*W+local;';assert needle in part;part=part.replace(needle,needle+'wave=__builtin_amdgcn_readfirstlane(wave);',1)
 s+='\n'+part
 for W in [1,2,4,8]:
  for m in ([False] if W==1 else [False,True]):
   n=f'{kind}_u{"m" if m else "i"}{W}'
   call=f'uniform_pair_body<{W},{str(m).lower()}>(a,b,c,rounds)' if kind=='mat' else f'uniform_load_body<{W},{str(m).lower()}>(a,b,c,as,bs,rounds)'
   s+=f'\nextern "C" __attribute__((global)) __attribute__((amdgpu_flat_work_group_size({W*32},{W*32}))) void {n}(const u8*a,const u8*b,float*c,uint as,uint bs,uint rounds){{{call};}}\n'
(out/'uniform.hip').write_text(s)
s=(out/'bench.cpp').read_text();a=s.index(' std::vector<Pair>pairs=');b=s.index(' FILE*csv=fopen(',a);pairs=[]
for kind in ['mat','load']:
 for suffix,W in [('i1',1),('i2',2),('m2',2)]:pairs.append(f'{{"{kind}_uniform_{suffix}",{{"{kind}_{suffix}",4,0,0,640,{W}}},{{"{kind}_u{suffix}",4,0,0,640,{W}}}}}')
s=s[:a]+' std::vector<Pair>pairs={\n'+',\n'.join(pairs)+'\n };\n'+s[b:];(out/'bench-uniform.cpp').write_text(s)
s=(h/'numeric.cpp').read_text().replace('../../hip_api.h',str(h.parents[3]/'Development/HIP/hip_api.h')).replace('std::string(kind)+"_"','std::string(kind)+"_u"');(out/'numeric-uniform.cpp').write_text(s)
