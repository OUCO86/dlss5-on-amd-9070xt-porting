# In-kernel phase timing for the three hot C32 kernels (dynamic, per wave), without touching kernel signatures.
# The _pair1 body reads SHADER_CYCLES (__builtin_readcyclecounter) at phase boundaries and accumulates the cycles spent
# inside every sync_window()/sync_owned_rows() (barrier wait). Lane 0 of each wave writes 12 u64 to a device buffer whose
# base the host stores in the module global `c32_trace` before each C32 launch (hipModuleGetGlobal + hipMemcpy).
from pathlib import Path
import re, shutil
here=Path(__file__).resolve().parent; root=here.parents[3]; out=Path('/tmp/c32-phase-trace'); out.mkdir(exist_ok=True)
s=(root/'hip/c32_fused_ffn_attention.hip').read_text()
a=s.index('template<bool HalfOutput,bool Mapped=false'); b=s.index('\nKERNEL ',a); body=s[a:b]
STAMPS=['T_entry','T_staged','T_ffn','T_ffn_written','T_qkv','T_scores','T_prob','T_av','T_proj','T_end','W_barrier','N_barrier']
# helpers injected before the body
helpers='''
typedef unsigned long long u64;
__attribute__((device)) u64* c32_trace;
DEV u64 cyc(){return __builtin_readcyclecounter();}
struct TraceState{u64 t[12];u64 wait;u64 n;};
DEV void sync_window_t(TraceState&ts){u64 a=cyc();WG_FENCE(3);__builtin_amdgcn_s_barrier();WG_FENCE(2);ts.wait+=cyc()-a;ts.n++;}
DEV void sync_owned_rows_t(TraceState&ts){
#if HIP_C32_LOCAL_QKV_SYNC
 WG_FENCE(3);WG_FENCE(2);
#else
 sync_window_t(ts);
#endif
}
'''
v=body.replace('c32_fused_body(','c32_trace_body(',1)
# state + entry stamp right after the shared declarations: anchor on the first LDS declaration line
anchor=' __attribute__((shared)) Scratch scratch;\n'
assert v.count(anchor)==1
v=v.replace(anchor,anchor+' TraceState ts{};ts.t[0]=cyc();\n',1)
v=v.replace('sync_window();','sync_window_t(ts);').replace('sync_owned_rows();','sync_owned_rows_t(ts);')
v=v.replace('#define ATTN_SYNC() sync_owned_rows()','#define ATTN_SYNC() sync_owned_rows_t(ts)').replace('#define ATTN_SYNC() sync_window()','#define ATTN_SYNC() sync_window_t(ts)')
def stamp_before(text,anchor,idx,count=1):
    assert text.count(anchor)==count,(anchor[:50],text.count(anchor))
    return text.replace(anchor,f' ts.t[{idx}]=cyc();\n'+anchor,1)
# 1 staged: before the pre-FFN sync (first occurrence of the LOCAL_FFN_SYNC block)
v=stamp_before(v,'#if HIP_C32_LOCAL_FFN_SYNC\n sync_owned_rows_t(ts);\n#else\n sync_window_t(ts);\n#endif\n',1,2)
# 2 ffn done: before the ALIAS_FFN_V phase-boundary sync
v=stamp_before(v,'#if HIP_C32_ALIAS_FFN_V && HIP_C32_REGISTER_FFN\n',2)
# 3 ffn written: before "// A single raw QKV plane"
v=stamp_before(v,' // A single raw QKV plane is reused after its norm has been packed separately.\n',3)
# 4 qkv done: before the LOCAL_QKV_SYNC sync_window that publishes K/V
v=stamp_before(v,'#if HIP_C32_LOCAL_QKV_SYNC\n sync_window_t(ts); // Attention reads K/V rows owned by all four waves.\n',4)
# 5 scores done: before the first ATTN_SYNC after the score loop
v=stamp_before(v,' ATTN_SYNC();\n // Scores no longer consume Q/K',5)
# 6 prob done: before "ATTN_SYNC();\n // Both AV column fragments"
v=stamp_before(v,' ATTN_SYNC();\n // Both AV column fragments',6)
# 7 av done: the ATTN_SYNC right after the AV block ("#endif\n\n ATTN_SYNC();\n for(uint ci")
v=stamp_before(v,' ATTN_SYNC();\n for(uint ci=0;ci<2;ci++)for(uint e=0;e<8;e++)packed[(first+gr()*8+e)*36+ci*16+rc()]=',7)
# 8 projection done: before the finish/RGB tail "if constexpr(Finish)" or the output loop end -> anchor on '#if HIP_C32_HOIST_PW' end: use the first 'if constexpr(Finish' occurrence
i=v.index('if constexpr(Finish'); j=v.rfind('\n',0,i)+1
v=v[:j]+' ts.t[8]=cyc();\n'+v[j:]
# 10 after the mapped index computation (start of the prefetch pass), 11 after pass-1 loads with an explicit wait
v=stamp_before(v,'#if HIP_C32_STAGE_PREFETCH\n',10)  # 2026-09-23: byte-chain staging sits between the flag and Pass 1; stamp at the flag
pass2='  #pragma unroll\n  for(uint j=0;j<16;j++){uint row=first+j;float v;\n'
assert v.count(pass2)==1
v=v.replace(pass2,' __asm__ volatile("s_wait_loadcnt 0x0" ::: "memory");ts.t[11]=cyc();\n'+pass2,1)
# 9 end + write: before the body's final closing brace
k=v.rstrip().rfind('}')
v=v[:k]+''' ts.t[9]=cyc();
 if(c32_trace&&(tid&31)==0){u64*o=c32_trace+((u64)__builtin_amdgcn_workgroup_id_x()*4+(tid>>5))*16;for(uint i=0;i<12;i++)o[i]=ts.t[i];o[12]=ts.wait;o[13]=ts.n;}
'''+v[k:]
code='#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_C32_DIAG_WEIGHTS 1\n'+s+helpers+'\n'+v+'\n'
names=re.findall(r'^void (c32_\w+)\(',s[b:],re.M)
for name in names:
    line=next(x for x in s[b:].splitlines() if x.startswith('void '+name+'('))
    code+='KERNEL __attribute__((amdgpu_flat_work_group_size(128,128))) C32_OCC\n'+line.replace('void '+name+'(',f'void {name}_pair1(',1).replace('c32_fused_body<','c32_trace_body<')+'\n'
(out/'kernel.hip').write_text(code); print('kernels',len(names),'stamps',STAMPS)
# ---- host
(out/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (root/'Development/HIP').glob('*.h'): shutil.copyfile(p,out/'Development/HIP'/p.name)
p=out/'Development/HIP/hip_api.h'; h=p.read_text()
h=h.replace('HIP_FN(hipModuleUnload,(Handle));','HIP_FN(hipModuleUnload,(Handle));HIP_FN(hipModuleGetGlobal,(void**,size_t*,Handle,const char*));',1)
h=h.replace('LOAD(hipModuleUnload);','LOAD(hipModuleUnload);LOAD(hipModuleGetGlobal);',1)
assert h.count('hipModuleGetGlobal')==2; p.write_text(h)
p=out/'Development/HIP/hip_reference_network.h'; n=p.read_text()
n=n.replace('class Network {','''class Network {
 unsigned pair_mode=0;bool tracing=false;void*trace_global=nullptr;std::vector<void*>trace_bufs;std::vector<unsigned>trace_groups;unsigned launch_in_frame=0,launches_per_frame=0;
 static const size_t TRACE_WAVES=40000*4,TRACE_U64=16;
 void TraceLaunch(const std::string&module,unsigned groups){if(!tracing||module!="c32_fused_ffn")return;if(launch_in_frame>=trace_bufs.size()){void*d=nullptr;api.Check(api.hipMalloc(&d,TRACE_WAVES*TRACE_U64*8),"trace buf");api.Check(api.hipMemsetAsync(d,0,TRACE_WAVES*TRACE_U64*8,stream),"trace zero");trace_bufs.push_back(d);trace_groups.push_back(groups);}
  void*base=trace_bufs[launch_in_frame];api.Check(api.hipStreamSynchronize(stream),"trace sync");api.Check(api.hipMemcpy(trace_global,&base,sizeof base,1),"trace ptr");launch_in_frame++;}
public:
 void SetPairMode(unsigned m){pair_mode=m;}
 void BeginTrace(){size_t sz=0;api.Check(api.hipModuleGetGlobal(&trace_global,&sz,modules.at("c32_fused_ffn"),"c32_trace"),"c32_trace global");tracing=true;launch_in_frame=0;}
 void EndFrame(){launches_per_frame=launch_in_frame;launch_in_frame=0;}
 unsigned LaunchesPerFrame()const{return launches_per_frame;}
 void DumpTrace(const std::string&prefix){api.Check(api.hipStreamSynchronize(stream),"trace dump sync");for(size_t i=0;i<trace_bufs.size();i++){std::vector<unsigned long long>v(TRACE_WAVES*TRACE_U64);api.Check(api.hipMemcpy(v.data(),trace_bufs[i],v.size()*8,2),"trace read");std::ofstream f(prefix+"-"+std::to_string(i)+".u64",std::ios::binary);f.write(reinterpret_cast<const char*>(v.data()),v.size()*8);}
  std::ofstream g(prefix+"-groups.txt");for(size_t i=0;i<trace_groups.size();i++)g<<i<<" "<<trace_groups[i]<<"\\n";}
private:
''',1)
old='for(unsigned repeat=0;repeat<repeats_here;repeat++)api.Check(api.hipModuleLaunchKernel(Fn(module,kernel),groups?groups:(count+255ull)/256,1,1,threads,1,1,0,stream,argv,nullptr),name);'
assert n.count(old)==1
n=n.replace(old,'if(module=="c32_fused_ffn"&&pair_mode){kernel+="_pair"+std::to_string(pair_mode);TraceLaunch(module,groups?groups:unsigned((count+255ull)/256));}\n  '+old,1)
p.write_text(n)
x=(root/'src/native_hip_network.h').read_text();a2=x.index('hip_reference::Options o;');b2=x.index('  const wchar_t*modules=',a2)
opts=x[a2:b2].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift','o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)','o.assets=argv[1]')
r=(root/'Development/HIP/experiments/vit-schedule-cause/runner.cpp.in').read_text()
a3=r.index(' for(unsigned frame=0;');b3=r.index('api.hipFree(x);',a3)
r=r[:a3]+(here/'trace.inc').read_text()+r[b3:]
(out/'network.cpp').write_text(r.replace('/* OPTIONS */',opts).replace('PASS ViT schedule controls','PASS C32 phase trace'))
print('host written')
