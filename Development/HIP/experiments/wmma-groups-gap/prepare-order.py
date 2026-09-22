from pathlib import Path
import runpy,json,math
h=Path(__file__).resolve().parent;out=Path('/tmp/wmma-groups-gap');runpy.run_path(str(h/'prepare.py'))
s=(out/'kernel.hip').read_text()
a=s.index('template<uint W,bool MGroup,bool Wide=true');b=s.index('template<uint W,bool MGroup> DEV void grouped_load_body',a);p=s[a:b].replace('grouped_pair_body','ordered_pair_body').replace('float*out,uint rounds){','float*out,uint rounds,uint stride){').replace(' uint first=wave/64*16,',' wave=(wave*stride)%2560;uint first=wave/64*16,')
s+='\n'+p+'\nKERNEL void order_mat(const u8*a,const u8*b,float*c,uint as,uint bs,uint rounds){ordered_pair_body<1,false>(a,b,c,rounds,as);}\n'
a=s.index('template<uint W,bool MGroup> DEV void grouped_load_body');b=s.index('\nextern "C" __attribute__((global)) __attribute__((amdgpu_flat_work_group_size(32,32))) void mat_i1',a);p=s[a:b].replace('grouped_load_body','ordered_load_body').replace(' uint first=wave/64*16,',' wave=(wave*as)%2560;uint first=wave/64*16,')
s+='\n'+p+'\nKERNEL void order_load(const u8*a,const u8*b,float*c,uint as,uint bs,uint rounds){ordered_load_body<1,false>(a,b,c,as,bs,rounds);}\n';(out/'order.hip').write_text(s)
s=(out/'bench.cpp').read_text();a=s.index(' std::vector<Pair>pairs=');b=s.index(' FILE*csv=fopen(',a);pairs=[]
for kind in ['mat','load']:
 pairs.append(f'{{"{kind}_order_control",{{"{kind}_i1",4,0,0,640,1}},{{"order_{kind}",4,1,0,640,1}}}}')
 for stride in [17,63,129]:pairs.append(f'{{"{kind}_stride{stride}",{{"order_{kind}",4,1,0,640,1}},{{"order_{kind}",4,{stride},0,640,1}}}}')
s=s[:a]+' std::vector<Pair>pairs={\n'+',\n'.join(pairs)+'\n };\n'+s[b:];(out/'bench-order.cpp').write_text(s)
s=(h/'numeric.cpp').read_text().replace('../../hip_api.h',str(h.parents[3]/'Development/HIP/hip_api.h'))
s=s.replace('for(const char*kind:{"mat","load"})for(unsigned W:{1u,2u,4u,8u})for(unsigned mapped=0;mapped<(W==1?1u:2u);mapped++){','for(const char*kind:{"mat","load"})for(unsigned stride:{1u,17u,63u,129u}){unsigned W=3;as=stride;')
s=s.replace('std::string name=std::string(kind)+"_"+(mapped?"m":"i")+std::to_string(W);','std::string name=std::string("order_")+kind;').replace('wave=mapped?local*64:local','wave=(local*stride)%2560').replace('fn,1,1,1,W*32,1,1','fn,3,1,1,32,1,1');(out/'numeric-order.cpp').write_text(s)
rows=[]
for stride in [1,17,63,129]:
 assert math.gcd(stride,2560)==1;v=[w*stride%2560 for w in range(2560)];assert sorted(v)==list(range(2560));rows.append(dict(stride=stride,bijection=True,groups=2560,threads=32))
r=h.parents[2]/'results/wmma-groups-gap-20260922';r.mkdir(exist_ok=True,parents=True);(r/'order-check.json').write_text(json.dumps(rows,indent=2)+'\n')
