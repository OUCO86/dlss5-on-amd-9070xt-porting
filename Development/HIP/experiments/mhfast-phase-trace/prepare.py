# Per-wave phase timing for mh_fast mh_ffn_fused_c256_frag_project_mapped_g128_qkv_bytein_fb (15 launches/frame, 512 threads).
# Stamps: entry, input staging done (before its barrier), expand loop done, activation+hidden write done (before barrier),
# contract done, end (projection/QKV/output). Every s_barrier in the body is timed as barrier wait.
from pathlib import Path
import re, shutil
here=Path(__file__).resolve().parent; root=here.parents[3]; out=Path('/tmp/mhfast-phase-trace'); out.mkdir(exist_ok=True)
src=(root/'hip/multihead_fast_padded.hip').read_text(); lines=src.split('\n')
start=next(i for i,l in enumerate(lines) if l.startswith('DEV void mh_ffn_qkv_body('))
assert lines[start-1].startswith('template<')
end=next(i for i in range(start,len(lines)) if lines[i]=='}')
body=lines[start:end+1]
entry=next(i for i,l in enumerate(body) if 'if(first>=tokens)return;' in l)
b1=next(i for i,l in enumerate(body) if i>entry and l==' __builtin_amdgcn_s_barrier();')
b2=next(i for i,l in enumerate(body) if l==' if constexpr(!ByteIn)__builtin_amdgcn_s_barrier();')
b3=next(i for i,l in enumerate(body) if i>b2 and l==' __builtin_amdgcn_s_barrier();')
assert body[b3+1].startswith(' f8 accum{};'),body[b3+1]
proj=next(i for i,l in enumerate(body) if l==' if constexpr(Project){')
newb=[]
for i,l in enumerate(body):
    if i==0: l=l.replace('mh_ffn_qkv_body(','mh_ffn_qkv_body_t(')
    if i==b1: newb.append(' ts.t[1]=cyc();')
    if i==b2: newb.append(' ts.t[2]=cyc();')
    if i==b3: newb.append(' ts.t[3]=cyc();')
    if i==proj: newb.append(' ts.t[4]=cyc();')
    if i==len(body)-1:
        newb.append(' ts.t[5]=cyc();')
        newb.append(' if(mh_trace&&(tid&31)==0){u64*o=mh_trace+((u64)__builtin_amdgcn_workgroup_id_x()*16+wave)*16;for(uint i=0;i<6;i++)o[i]=ts.t[i];o[12]=ts.wait;o[13]=ts.n;}')
    l=l.replace('__builtin_amdgcn_s_barrier();','bar_t(ts);')
    newb.append(l)
    if i==entry: newb.append(' TraceState ts{};ts.t[0]=cyc();')
helpers='''
typedef unsigned long long u64;
__attribute__((device)) u64* mh_trace;
DEV u64 cyc(){return __builtin_readcyclecounter();}
struct TraceState{u64 t[12];u64 wait;u64 n;};
DEV void bar_t(TraceState&ts){u64 a=cyc();__builtin_amdgcn_s_barrier();ts.wait+=cyc()-a;ts.n++;}
'''
kdef=next(i for i,l in enumerate(lines) if 'void mh_ffn_fused_c256_frag_project_mapped_g128_qkv_bytein_fb(' in l)
kline=lines[kdef].replace('void mh_ffn_fused_c256_frag_project_mapped_g128_qkv_bytein_fb(','void mh_ffn_fused_c256_frag_project_mapped_g128_qkv_bytein_fb_pair1(').replace('mh_ffn_qkv_body<','mh_ffn_qkv_body_t<')
assert 'body_t<' in kline
code='#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_FFN_HOIST_RES 2\n'+src+'\n'+helpers+lines[start-1]+'\n'+'\n'.join(newb)+'\n'+kline+'\n'
(out/'kernel.hip').write_text(code); print('body',len(body),'stamps at',entry,b1,b2,b3,proj)
# host
(out/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (root/'Development/HIP').glob('*.h'): shutil.copyfile(p,out/'Development/HIP'/p.name)
p=out/'Development/HIP/hip_api.h'; h=p.read_text()
h=h.replace('HIP_FN(hipModuleUnload,(Handle));','HIP_FN(hipModuleUnload,(Handle));HIP_FN(hipModuleGetGlobal,(void**,size_t*,Handle,const char*));',1).replace('LOAD(hipModuleUnload);','LOAD(hipModuleUnload);LOAD(hipModuleGetGlobal);',1)
assert h.count('hipModuleGetGlobal')==2; p.write_text(h)
p=out/'Development/HIP/hip_reference_network.h'; n=p.read_text()
n=n.replace('class Network {','''class Network {
 unsigned pair_mode=0;bool tracing=false;void*trace_global=nullptr;std::vector<void*>trace_bufs;std::vector<unsigned>trace_groups;unsigned launch_in_frame=0,launches_per_frame=0;
 static const size_t TRACE_WAVES=8000*16,TRACE_U64=16;
 void TraceLaunch(unsigned groups){if(!tracing)return;if(launch_in_frame>=trace_bufs.size()){void*d=nullptr;api.Check(api.hipMalloc(&d,TRACE_WAVES*TRACE_U64*8),"trace buf");api.Check(api.hipMemsetAsync(d,0,TRACE_WAVES*TRACE_U64*8,stream),"trace zero");trace_bufs.push_back(d);trace_groups.push_back(groups);}
  void*base=trace_bufs[launch_in_frame];api.Check(api.hipStreamSynchronize(stream),"trace sync");api.Check(api.hipMemcpy(trace_global,&base,sizeof base,1),"trace ptr");launch_in_frame++;}
public:
 void SetPairMode(unsigned m){pair_mode=m;}
 void BeginTrace(){size_t sz=0;api.Check(api.hipModuleGetGlobal(&trace_global,&sz,modules.at("mh_fast"),"mh_trace"),"mh_trace global");if(sz!=8)throw std::runtime_error("mh_trace size");tracing=true;launch_in_frame=0;}
 void EndFrame(){launches_per_frame=launch_in_frame;launch_in_frame=0;}
 unsigned LaunchesPerFrame()const{return launches_per_frame;}
 void DumpTrace(const std::string&prefix){api.Check(api.hipStreamSynchronize(stream),"trace dump sync");for(size_t i=0;i<trace_bufs.size();i++){std::vector<unsigned long long>v(TRACE_WAVES*TRACE_U64);api.Check(api.hipMemcpy(v.data(),trace_bufs[i],v.size()*8,2),"trace read");std::ofstream f(prefix+"-"+std::to_string(i)+".u64",std::ios::binary);f.write(reinterpret_cast<const char*>(v.data()),v.size()*8);}
  std::ofstream g(prefix+"-groups.txt");for(size_t i=0;i<trace_groups.size();i++)g<<i<<" "<<trace_groups[i]<<"\\n";}
private:
''',1)
old='for(unsigned repeat=0;repeat<repeats_here;repeat++)api.Check(api.hipModuleLaunchKernel(Fn(module,kernel),groups?groups:(count+255ull)/256,1,1,threads,1,1,0,stream,argv,nullptr),name);'
assert n.count(old)==1
n=n.replace(old,'if(module=="mh_fast"&&kernel=="mh_ffn_fused_c256_frag_project_mapped_g128_qkv_bytein_fb"&&pair_mode){kernel+="_pair1";TraceLaunch(groups?groups:unsigned((count+255ull)/256));}\n  '+old,1)
p.write_text(n)
x=(root/'src/native_hip_network.h').read_text();a2=x.index('hip_reference::Options o;');b2=x.index('  const wchar_t*modules=',a2)
opts=x[a2:b2].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift','o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)','o.assets=argv[1]')
r=(root/'Development/HIP/experiments/vit-schedule-cause/runner.cpp.in').read_text()
a3=r.index(' for(unsigned frame=0;');b3=r.index('api.hipFree(x);',a3)
r=r[:a3]+(here/'trace.inc').read_text()+r[b3:]
(out/'network.cpp').write_text(r.replace('/* OPTIONS */',opts).replace('PASS ViT schedule controls','PASS MHFAST phase trace'))
print('host written')
