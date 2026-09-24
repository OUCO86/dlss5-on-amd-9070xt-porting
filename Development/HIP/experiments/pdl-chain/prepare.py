# Programmatic-dependent-launch emulation for the C64/C128/C256 block chains (FFN/QKV producer <-> window
# attention-project). Same stream, every chain launch after the chain head is submitted with hipExtAnyOrderLaunch (no
# AQL barrier bit) so the CP dispatches it while the previous launch drains; correctness comes from per-tile flags:
#   FFN group (16 tokens of the lattice) publishes ffn_flags[tile]=epoch after its stores (release fence + barrier);
#   attention group (one 8x8 window) waits ffn_flags[tile] >= epoch for the tiles its 64 tokens live in, and after its
#   stores publishes attn_flags[window]=epoch;
#   the next block's FFN group waits attn_flags[window] >= epoch for the producer-lattice windows that hold the image
#   pixels its 16 tokens map to (up to 3 windows per lattice row, at most 2 rows).
# Flags carry monotonic epochs in an 8-deep ring of slot arrays and never need clearing; the host keeps the last few
# blocks' tensors alive so the pool cannot hand a buffer still being read by an in-flight launch to a later launch.
# Math, layouts, module set: unchanged (the _pdl kernels are extra exports of the prod7 sources). Output must stay
# bit-exact against the timeline expected.f32. ABBA host: mode 0 = normal launches, mode 1 = PDL.
from pathlib import Path
import re, shutil
here=Path(__file__).resolve().parent; root=here.parents[3]; out=Path('/tmp/pdl-chain'); out.mkdir(exist_ok=True)

HELPERS_FFN='''
// ---- PDL emulation helpers (experiment pdl-chain, 2026-09-25) ----
DEV void pdl_ffn_wait(const uint*pflags,uint pepoch,uint pww,uint psx,uint psy,uint tokens,uint width,uint height,uint workw,uint sx,uint sy){
#ifdef PDL_NO_WAIT
 return;
#endif
 if(!pflags)return;
 uint tid=__builtin_amdgcn_workitem_id_x(),first=__builtin_amdgcn_workgroup_id_x()*16;
 if(tid<16){uint p=first+tid;if(p<tokens){int x=int(p%workw)-int(sx),y=int(p/workw)-int(sy);
  if(x>=0&&y>=0&&x<int(width)&&y<int(height)){uint idx=((uint(y)+psy)/8)*(pww/8)+(uint(x)+psx)/8;
   while(__hip_atomic_load(pflags+idx,__ATOMIC_RELAXED,__HIP_MEMORY_SCOPE_AGENT)<pepoch)__builtin_amdgcn_s_sleep(1);}}}
 __builtin_amdgcn_s_barrier();
#ifndef PDL_ACQUIRE
 /* no per-group acquire: the dispatch packet's own acquire fence already invalidated L0/L1 for this launch, and the
    only lines cached after that are ones loaded after their tile's flag was seen, i.e. final producer data. A per-group
    gl0/gl1 invalidate also evicts the weights every resident group on the CU keeps hot (measured ~0.2 ms/frame). */
#else
 __builtin_amdgcn_fence(__ATOMIC_ACQUIRE,"agent");
#endif
}
DEV void pdl_publish(uint*flags,uint epoch,uint slot){
#ifdef PDL_NO_PUBLISH
 return;
#endif
 /* per wave: no group barrier; each wave waits for its own stores (release) and bumps the tile counter. Consumers wait
    for counter >= waves_per_group x uses_of_this_slot (host-tracked cumulative target). `epoch` unused here. */
 __builtin_amdgcn_fence(__ATOMIC_RELEASE,"agent");
 if(__builtin_amdgcn_workitem_id_x()%32==0)__hip_atomic_fetch_add(flags+slot,1u,__ATOMIC_RELAXED,__HIP_MEMORY_SCOPE_AGENT);
}
'''
HELPERS_ATTN='''
// ---- PDL emulation helpers (experiment pdl-chain, 2026-09-25) ----
DEV void pdl_attn_wait(const uint*fflags,uint fepoch,uint width,uint height){
#ifdef PDL_NO_WAIT
 return;
#endif
 uint windows=(width/8)*(height/8),win=__builtin_amdgcn_workgroup_id_x(),tid=__builtin_amdgcn_workitem_id_x();
 if(tid<64&&win<windows){uint p=raster(win,tid,width);
  while(__hip_atomic_load(fflags+p/16,__ATOMIC_RELAXED,__HIP_MEMORY_SCOPE_AGENT)<fepoch)__builtin_amdgcn_s_sleep(1);}
 __builtin_amdgcn_s_barrier();
#ifndef PDL_ACQUIRE
 /* no per-group acquire: the dispatch packet's own acquire fence already invalidated L0/L1 for this launch, and the
    only lines cached after that are ones loaded after their tile's flag was seen, i.e. final producer data. A per-group
    gl0/gl1 invalidate also evicts the weights every resident group on the CU keeps hot (measured ~0.2 ms/frame). */
#else
 __builtin_amdgcn_fence(__ATOMIC_ACQUIRE,"agent");
#endif
}
DEV void pdl_publish(uint*flags,uint epoch,uint slot){
#ifdef PDL_NO_PUBLISH
 return;
#endif
 /* per wave: no group barrier; each wave waits for its own stores (release) and bumps the tile counter. Consumers wait
    for counter >= waves_per_group x uses_of_this_slot (host-tracked cumulative target). `epoch` unused here. */
 __builtin_amdgcn_fence(__ATOMIC_RELEASE,"agent");
 if(__builtin_amdgcn_workitem_id_x()%32==0)__hip_atomic_fetch_add(flags+slot,1u,__ATOMIC_RELAXED,__HIP_MEMORY_SCOPE_AGENT);
}
'''
FFN_NAMES=sorted(set(re.findall(r'void (mh_ffn_fused_c(?:64|128|256)_(?:frag_)?project(?:_mapped)?_g128_qkv(?:_bytein)?_fb)\(',(root/'hip/multihead_fast_padded.hip').read_text())))
ATTN_NAMES=['c64_attention_project_fb_bout_diag','c64_attention_project_fb_diag','c128_attention_project_fb_bout_diag','c128_attention_project_fb_diag',
 'c256_attention_project_fb_bout_diag','c256_attention_project_fb_diag']

# mh_fast (prod7 recipe: ISA_HALF + PREPACKED + FFN_HOIST_RES 2 + LINE_STORES 1)
s=(root/'hip/multihead_fast_padded.hip').read_text()
assert s.count('#define HIP_FFN_LINE_STORES 0')==1
s=s.replace('#define HIP_FFN_LINE_STORES 0','#define HIP_FFN_LINE_STORES 1',1)
gen=[HELPERS_FFN]
for name in FFN_NAMES:
    m=re.search(r'KERNEL __attribute__\(\(amdgpu_flat_work_group_size\((\d+),\d+\)\)\) void '+re.escape(name)+r'\((const float\*in,[^)]*)\)\{(mh_ffn_qkv_body<[^>]*>)\(([^)]*)\);\}',s)
    assert m,name
    T,params,body,args=m.groups()
    gen.append(f'KERNEL __attribute__((amdgpu_flat_work_group_size({T},{T}))) void {name}_pdl({params},const uint*pflags,uint pepoch,uint pww,uint psx,uint psy,uint*fflags,uint fepoch){{\n'
               f' pdl_ffn_wait(pflags,pepoch,pww,psx,psy,tokens,width,height,workw,sx,sy);\n {body}({args});\n pdl_publish(fflags,fepoch,__builtin_amdgcn_workgroup_id_x());\n}}\n')
MHFAST='#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_FFN_HOIST_RES 2\n'+s+'\n'+''.join(gen)
for v,d in (('','' ),('nowait','#define PDL_NO_WAIT 1\n'),('nopublish','#define PDL_NO_PUBLISH 1\n')):(out/('mhfast'+(('.'+v) if v else '')+'.generated.hip')).write_text(d+MHFAST)

# mh_fused (ISA_HALF + MH_RTZ_ISA)
s=(root/'hip/multihead_fused_attention.hip').read_text()
gen=[HELPERS_ATTN]
for name in ATTN_NAMES:
    m=re.search(r'\nvoid '+re.escape(name)+r'\((const unsigned char\*normalized,[^)]*)\)\{(c\d+_attention_project_body<[^>]*>)\(([^)]*)\);\}',s)
    assert m,name
    params,body,args=m.groups();T=256 if name.startswith('c64_') else 512
    gen.append(f'KERNEL __attribute__((amdgpu_flat_work_group_size({T},{T})))\nvoid {name}_pdl({params},const uint*fflags,uint fepoch,uint*aflags,uint aepoch){{\n'
               f' pdl_attn_wait(fflags,fepoch,width,height);\n {body}({args});\n pdl_publish(aflags,aepoch,__builtin_amdgcn_workgroup_id_x());\n}}\n')
MHFUSED='#define HIP_ISA_HALF 1\n#define HIP_MH_RTZ_ISA 1\n'+s+'\n'+''.join(gen)
for v,d in (('','' ),('nowait','#define PDL_NO_WAIT 1\n'),('nopublish','#define PDL_NO_PUBLISH 1\n')):(out/('mhfused'+(('.'+v) if v else '')+'.generated.hip')).write_text(d+MHFUSED)

# host
shutil.rmtree(out/'Development',ignore_errors=True);(out/'Development/HIP').mkdir(parents=True)
for p in (root/'Development/HIP').glob('*.h'):shutil.copyfile(p,out/'Development/HIP'/p.name)
p=out/'Development/HIP/hip_reference_network.h';h=p.read_text()
def rep(old,new,count=1):
    global h;assert h.count(old)==count,(old[:60],h.count(old));h=h.replace(old,new)
rep('class Network {','''class Network {
 // ---- PDL emulation (experiment pdl-chain) ----
 unsigned pdl_mode=0,pdl_calls=0,pdl_epoch=1,pdl_ring=0;unsigned*pdl_flags=nullptr;bool pdl_anyorder=false;std::deque<Tensor>pdl_keep;
 struct PdlPrev{unsigned*flags=nullptr;unsigned epoch=0,ww=0,sx=0,sy=0;}pdl_prev;unsigned*pdl_ffn_flags=nullptr;unsigned pdl_ffn_epoch=0;
 int(*ext_launch)(Handle,unsigned,unsigned,unsigned,unsigned,unsigned,unsigned,size_t,Handle,void**,void**,Handle,Handle,unsigned)=nullptr;
 static constexpr unsigned PDL_SLOTS=16384,PDL_RING=64;
 std::map<std::tuple<unsigned,unsigned,unsigned,unsigned>,unsigned>pdl_slot_of;std::vector<unsigned>pdl_total;unsigned pdl_last_target=0;
 /* one counter array per (kind,c,ww,hh): every use increments every tile of that geometry, so cumulative per-slot targets stay exact */
 unsigned*PdlSlot(unsigned kind,unsigned c,unsigned ww,unsigned hh,unsigned waves){auto key=std::make_tuple(kind,c,ww,hh);auto it=pdl_slot_of.find(key);if(it==pdl_slot_of.end()){if(pdl_slot_of.size()>=PDL_RING)throw std::runtime_error("pdl slots exhausted");it=pdl_slot_of.emplace(key,unsigned(pdl_slot_of.size())).first;pdl_total.push_back(0);}unsigned s=it->second;pdl_total[s]+=waves;pdl_last_target=pdl_total[s];return pdl_flags+size_t(s)*PDL_SLOTS;}
 static bool PdlChainHead(U block){return block==5||block==9||block==15||block==23||block==40||block==48||block==56||block==62;}
 public: void SetPairMode(unsigned m){static std::vector<unsigned>t=[]{std::vector<unsigned>v{0,7,1,9,17};if(const char*e=std::getenv("DLSS5_PDL_TABLE")){v.clear();std::string x=e;size_t i=0;while(i<=x.size()){size_t j=x.find(',',i);if(j==std::string::npos)j=x.size();v.push_back(unsigned(std::stoul(x.substr(i,j-i))));i=j+1;}}return v;}();pdl_mode=t.at(m);pdl_calls=0;} /* bit0 pdl kernels, bit1 any-order FFN, bit2 any-order attention */ unsigned PairCalls()const{return pdl_calls;} private:''')
rep('#include <fstream>','#include <fstream>\n#include <deque>\n#include <map>\n#include <tuple>')
# launch: any-order through hipExtModuleLaunchKernel when flagged
rep('api.Check(api.hipModuleLaunchKernel(Fn(module,kernel),groups?groups:(count+255ull)/256,1,1,threads,1,1,0,stream,argv,nullptr),name);',
    '{unsigned gg=unsigned(groups?groups:(count+255ull)/256);if(pdl_anyorder){++pdl_calls;api.Check(ext_launch(Fn(module,kernel),gg*threads,1,1,threads,1,1,0,stream,argv,nullptr,nullptr,nullptr,1u),name);}else api.Check(api.hipModuleLaunchKernel(Fn(module,kernel),gg,1,1,threads,1,1,0,stream,argv,nullptr),name);}')
# flags buffer + ext entry point after the fused MH module load
rep('modules["mh_fast"]=m;}','modules["mh_fast"]=m;}\n api.Load(ext_launch,"hipExtModuleLaunchKernel");api.Check(api.hipMalloc((void**)&pdl_flags,size_t(PDL_SLOTS)*PDL_RING*4),"pdl flags");api.Check(api.hipMemsetAsync(pdl_flags,0,size_t(PDL_SLOTS)*PDL_RING*4,stream),"pdl flags zero");')
# Body: chain-head reset + PDL FFN launch + lifetime ring
rep(' Tensor Body(Tensor input,U w,U h,U c,U shift,U block,bool raw,bool byte_in=false,bool byte_out=false){',
    ' Tensor Body(Tensor input,U w,U h,U c,U shift,U block,bool raw,bool byte_in=false,bool byte_out=false){if(PdlChainHead(block))pdl_prev={};pdl_ffn_flags=nullptr;')
old_ffn='if(producer_norm)Run("mh_fast",name.c_str(),size_t(n)*c,P(packed),fw,ffn_frag?PackedMhWeightQkvFragOnly(Block(block,"attention"),c):PackedMhWeight(Block(block,"attention"),c,true),P(ffn),P(producer_norm),n,w,h,ww,sx,sy);'
new_ffn='''if(producer_norm){void*qw=ffn_frag?PackedMhWeightQkvFragOnly(Block(block,"attention"),c):PackedMhWeight(Block(block,"attention"),c,true);
   if(pdl_mode&&(c==64||c==128||c==256)&&byte_feature&&(identity||mapped)&&(identity||opt.mh_project_crop)){
    const bool head=!pdl_prev.flags;unsigned*fflags=PdlSlot(0,c,ww,hh,c*2/32);unsigned fepoch=pdl_last_target;const unsigned*pflags=(head||(pdl_mode&8))?nullptr:pdl_prev.flags;unsigned pepoch=head?0u:pdl_prev.epoch,pww=head?8u:pdl_prev.ww,psx=head?0u:pdl_prev.sx,psy=head?0u:pdl_prev.sy;
    pdl_anyorder=!head&&(pdl_mode&2);Run("mh_fast",(name+"_pdl").c_str(),size_t(n)*c,P(packed),fw,qw,P(ffn),P(producer_norm),n,w,h,ww,sx,sy,pflags,pepoch,pww,psx,psy,(pdl_mode&16)?nullptr:fflags,fepoch);pdl_anyorder=false;pdl_ffn_flags=fflags;pdl_ffn_epoch=fepoch;}
   else Run("mh_fast",name.c_str(),size_t(n)*c,P(packed),fw,qw,P(ffn),P(producer_norm),n,w,h,ww,sx,sy);}'''
rep(old_ffn,new_ffn)
old_tail='if(!identity&&!crop)Run("mh","mh_shift_crop",size_t(w)*h*c,P(attended),P(out),w,h,ww,sx,sy,c);Stage("block"+std::to_string(block),out);return out;}'
new_tail='if(!identity&&!crop)Run("mh","mh_shift_crop",size_t(w)*h*c,P(attended),P(out),w,h,ww,sx,sy,c);if(pdl_mode){pdl_keep.push_back(input);pdl_keep.push_back(ffn);pdl_keep.push_back(producer_norm);pdl_keep.push_back(out);while(pdl_keep.size()>32)pdl_keep.pop_front();}Stage("block"+std::to_string(block),out);return out;}'
rep(old_tail,new_tail)
# AttentionFast: PDL twin when the FFN of this block published flags
old_attn='Run("mh_fused",project.c_str(),windows,P(norm),weights,P(input),P(out),w,h,U(raw?3:rounded_output?0:4),cropw,croph,sx,sy);return out;}'
new_attn='''if(pdl_ffn_flags&&(project.size()>8&&project.compare(project.size()-8,8,"_fb_diag")==0||project.size()>13&&project.compare(project.size()-13,13,"_fb_bout_diag")==0)){
    unsigned*aflags=PdlSlot(1,c,w,h,c==64?8u:16u);unsigned aepoch=pdl_last_target;const unsigned*ff=(pdl_mode&8)?nullptr:pdl_ffn_flags;unsigned fe=pdl_ffn_epoch;pdl_anyorder=(pdl_mode&4)!=0;
    Run("mh_fused",(project+"_pdl").c_str(),windows,P(norm),weights,P(input),P(out),w,h,U(raw?3:rounded_output?0:4),cropw,croph,sx,sy,ff,fe,(pdl_mode&16)?nullptr:aflags,aepoch);pdl_anyorder=false;
    pdl_prev={aflags,aepoch,w,sx,sy};pdl_ffn_flags=nullptr;return out;}
   pdl_prev={};pdl_ffn_flags=nullptr;Run("mh_fused",project.c_str(),windows,P(norm),weights,P(input),P(out),w,h,U(raw?3:rounded_output?0:4),cropw,croph,sx,sy);return out;}'''
rep(old_attn,new_attn)
p.write_text(h)
x=(root/'src/native_hip_network.h').read_text();a=x.index('hip_reference::Options o;');b=x.index('  const wchar_t*modules=',a)
opts=x[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift','o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)','o.assets=argv[1]')
r=(root/'Development/HIP/experiments/vit-schedule-cause/runner.cpp.in').read_text()
a=r.index(' for(unsigned frame=0;');b=r.index('api.hipFree(x);',a)
r=r[:a]+(here/'timing.inc').read_text()+r[b:]
(out/'network.cpp').write_text(r.replace('/* OPTIONS */',opts).replace('PASS ViT schedule controls','PASS pdl chain'))
print('written',out)
