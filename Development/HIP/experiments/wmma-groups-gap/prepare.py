from pathlib import Path
import runpy
h=Path(__file__).resolve().parent;root=h.parents[3];old=h.parent/'wmma-width-gap';out=Path('/tmp/wmma-groups-gap');out.mkdir(exist_ok=True)
base=(old/'kernel.hip').read_text().replace('DEV uint lane(){return __builtin_amdgcn_workitem_id_x();}','DEV uint lane(){return __builtin_amdgcn_workitem_id_x()&31;}')
code=base+'\n'+(old/'load-multi.inc').read_text()
a=base.index('template<bool Wide,bool Interleave=true> DEV void pair_body(');b=base.index('\nKERNEL void pair64',a);body=base[a:b]
body=body.replace('template<bool Wide,bool Interleave=true> DEV void pair_body(', 'template<uint W,bool MGroup,bool Wide=true,bool Interleave=true> DEV void grouped_pair_body(',1)
setup='uint local=__builtin_amdgcn_workitem_id_x()/32;uint wave=MGroup?(block()/64*W+local)*64+block()%64:block()*W+local;'
body=body.replace(' uint first=block()/64*16,col=block()%64*64,', ' '+setup+'\n uint first=wave/64*16,col=wave%64*64,').replace('out[block()*32+lane()]','out[wave*32+lane()]');code+='\n'+body
body=(old/'load-multi.inc').read_text().replace('KERNEL void pair128_loadonly_multi(', 'template<uint W,bool MGroup> DEV void grouped_load_body(',1)
body=body.replace(' uint first=block()/64*16,col=block()%64*64,',' '+setup+'\n uint first=wave/64*16,col=wave%64*64,').replace('out[block()*32+lane()]','out[wave*32+lane()]');code+='\n'+body
for kind in ['mat','load']:
 for W in [1,2,4,8]:
  for perm in ([False] if W==1 else [False,True]):
   name=f'{kind}_{"m" if perm else "i"}{W}'
   call=f'grouped_pair_body<{W},{str(perm).lower()}>(a,b,c,rounds)' if kind=='mat' else f'grouped_load_body<{W},{str(perm).lower()}>(a,b,c,as,bs,rounds)'
   code+=f'\nextern "C" __attribute__((global)) __attribute__((amdgpu_flat_work_group_size({W*32},{W*32}))) void {name}(const u8*a,const u8*b,float*c,uint as,uint bs,uint rounds){{{call};}}\n'
(out/'kernel.hip').write_text(code)
runpy.run_path(str(old/'prepare-grid.py'));s=Path('/tmp/wmma-width-gap/bench-grid.cpp').read_text().replace('tokens=640;', 'tokens=640,waves=1;')
a=s.index(' std::vector<Pair>pairs=');b=s.index(' FILE*csv=fopen(',a);pairs=[]
for kind,ref in [('mat','pair128'),('load','pair128_loadonly_multi')]:
 pairs.append(f'{{"{kind}_control",{{"{ref}",4,0,0,640,1}},{{"{kind}_i1",4,0,0,640,1}}}}')
 for W in [2,4,8]:
  pairs.append(f'{{"{kind}_group{W}",{{"{kind}_i1",4,0,0,640,1}},{{"{kind}_i{W}",4,0,0,640,{W}}}}}')
  pairs.append(f'{{"{kind}_map{W}",{{"{kind}_i{W}",4,0,0,640,{W}}},{{"{kind}_m{W}",4,0,0,640,{W}}}}}')
s=s[:a]+' std::vector<Pair>pairs={\n'+',\n'.join(pairs)+'\n };\n'+s[b:]
s=s.replace('groups=c.tokens/16*64;Handle fn{};', 'unsigned logical_waves=c.tokens/16*64;groups=logical_waves/c.waves;unsigned threads=c.waves*32;if(logical_waves%c.waves)throw std::runtime_error("group shape");Handle fn{};')
s=s.replace('fn,groups,1,1,32,1,1','fn,groups,1,1,threads,1,1').replace('std::vector<float>v(size_t(groups)*32)','std::vector<float>v(size_t(logical_waves)*32)')
s=s.replace('find("loadonly")','find("load")').replace('double(groups)*rounds*16*8192','double(logical_waves)*rounds*16*8192')
s=s.replace('tokens,rounds,launches','tokens,waves,groups,threads,rounds,launches').replace('"%s,%u,%s,%u,%u,%u,%u,%u,%u,%.9f','"%s,%u,%s,%u,%u,%u,%u,%u,%u,%u,%u,%u,%.9f').replace('c.as,c.bs,c.tokens,rounds,n,us,tf','c.as,c.bs,c.tokens,c.waves,groups,threads,rounds,n,us,tf')
(out/'bench.cpp').write_text(s)
