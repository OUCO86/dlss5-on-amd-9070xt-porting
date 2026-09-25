# PDL emulation extended to the C512 chains (blocks 23-30, 40-47): 7 launches per block (mh_shift_pack, split_mix_blocked_h16w,
# split_ffn_fused_fp8_t8, split_projection_frag, mh_qkv_normalize_frag_c512, mh_attention_fused_fp8_out,
# mh_attention_project_frag_c512). Uniform tile = 16 consecutive lattice tokens (tokens are a multiple of 64). Every
# stage waits for its own tile of the previous stage (attention: the 8 row segments of its window; shift_pack: the previous
# lattice's tile holding the image pixel of its token), publishes its tile per wave. Per-tile contributions (host targets):
# shift_pack 32 groups x 8 waves = 256, mix 8x1, ffn_t8 8x4, projection 8x1, qkv 24x1, attention 2 segments x 16 heads x 4 waves
# = 128, attention_project 8x1. Host: chain head shift_pack normal launch, all else any-order. ABBA modes: 0 normal,
# 15 = C64-256 (7) + C512 (8), 7 = C64-256 only, 8 = C512 only. Bit-exact enforced. Builds on the prod8 sources (already
# carrying the C64-256 twins) -- generated over the current tree.
from pathlib import Path
import re, shutil
here=Path(__file__).resolve().parent; root=here.parents[3]; out=Path('/tmp/pdl-c512'); out.mkdir(exist_ok=True)

HELP='''
#if HIP_PDL_KERNELS
// ---- C512 chain PDL helpers (experiment pdl-c512, 2026-09-25) ----
DEV void pdl512_wait(const uint*f,uint t,uint tile,bool multiwave){
 if(!f)return;
 if(__builtin_amdgcn_workitem_id_x()==0)while(__hip_atomic_load(f+tile,__ATOMIC_RELAXED,__HIP_MEMORY_SCOPE_AGENT)<t)__builtin_amdgcn_s_sleep(1);
 if(multiwave)__builtin_amdgcn_s_barrier();
}
DEV void pdl512_pub(uint*f,uint tile){
 __builtin_amdgcn_fence(__ATOMIC_RELEASE,"agent");
 if(__builtin_amdgcn_workitem_id_x()%32==0)__hip_atomic_fetch_add(f+tile,1u,__ATOMIC_RELAXED,__HIP_MEMORY_SCOPE_AGENT);
}
'''
def cut_kernel(src,name):
    m=re.search(r'void '+re.escape(name)+r'\(',src);assert m,name
    ls=src.rfind('\n',0,m.start())+1            # start of the signature line
    inline=src[ls:m.start()]                        # e.g. 'WAVE ' / 'FASTWAVE ' / '' on the same line
    prev_ls=src.rfind('\n',0,ls-1)+1;prev=src[prev_ls:ls]
    attr=prev if (prev.startswith('KERNEL') and 'void' not in prev) else ''
    b=src.index('\n}\n',m.start())+3
    return attr,inline,src[m.start():b]
def twin(src,name,extra_params,wait_stmt,pub_stmt):
    attr,inline,fn=cut_kernel(src,name)
    sig_end=fn.index('){')
    sig=fn[:sig_end].replace('void '+name+'(','void '+name+'_pdl(',1)+','+extra_params+'){'
    body=fn[sig_end+2:]
    assert body.endswith('\n}\n'),name
    body=body[:-3]
    nl=body.index('\n',1 if body.startswith('\n') else 0)
    return '\n'+attr+inline+sig+body[:nl+1]+' '+wait_stmt+'\n'+body[nl+1:]+'\n '+pub_stmt+'\n}\n'
def emit(path_in,defines,twins_fn,path_out,helpers=True):
    s=(root/'hip'/path_in).read_text()
    gen=twins_fn(s)
    text=''.join(f'#define {d}\n' for d in defines)+s+'\n'+(HELP if helpers else '')+''.join(gen)+('#endif\n' if helpers else '')
    (out/path_out).write_text(text)

# deep_fast-packed
def deep_twins(s):
    g=[]
    g.append(twin(s,'split_mix_blocked_h16w','const uint*pf,uint pt,uint*of','pdl512_wait(pf,pt,first/16,false);','pdl512_pub(of,first/16);'))
    g.append(twin(s,'split_ffn_fused_fp8_t8','const uint*pf,uint pt,uint*of','pdl512_wait(pf,pt,first/16,true);','pdl512_pub(of,first/16);'))
    g.append(twin(s,'split_projection_frag','const uint*pf,uint pt,uint*of','pdl512_wait(pf,pt,first/16,false);','pdl512_pub(of,first/16);'))
    return g
emit('deep_fast.hip',['HIP_ISA_HALF 1','HIP_PREPACKED_WEIGHTS 1','HIP_BRANCHLESS_F 1','HIP_PDL_KERNELS 1'],deep_twins,'deep_fast-packed.generated.hip')
# mh_fast (prod8 recipe; already has HIP_PDL_KERNELS block with pdl_publish etc.)
def mhfast_twins(s):
    g=[]
    g.append(twin(s,'mh_qkv_normalize_frag_c512','const uint*pf,uint pt,uint*of','pdl512_wait(pf,pt,first/16,false);','pdl512_pub(of,first/16);'))
    g.append(twin(s,'mh_attention_project_frag_c512','const uint*pf,uint pt,uint*of','pdl512_wait(pf,pt,first/16,false);','pdl512_pub(of,first/16);'))
    return g
emit('multihead_fast_padded.hip',['HIP_ISA_HALF 1','HIP_PREPACKED_WEIGHTS 1','HIP_FFN_HOIST_RES 2','HIP_FFN_LINE_STORES 1'],mhfast_twins,'multihead-fast-padded-wave-packed.generated.hip')
# mh_fused: attention fused (window,head) groups of 4 waves
def mhfused_twins(s):
    wait='''if(pf){uint t=__builtin_amdgcn_workitem_id_x();if(t<8){uint tile=raster(win,t*8,width)/16;while(__hip_atomic_load(pf+tile,__ATOMIC_RELAXED,__HIP_MEMORY_SCOPE_AGENT)<pt)__builtin_amdgcn_s_sleep(1);}__builtin_amdgcn_s_barrier();}'''
    pub='''__builtin_amdgcn_fence(__ATOMIC_RELEASE,"agent");if(__builtin_amdgcn_workitem_id_x()%32==0)for(uint s=0;s<8;s++)__hip_atomic_fetch_add(of+raster(win,s*8,width)/16,1u,__ATOMIC_RELAXED,__HIP_MEMORY_SCOPE_AGENT);'''
    attr,inline,fn=cut_kernel(s,'mh_attention_fused_fp8_out')
    sig_end=fn.index('){');sig=inline+fn[:sig_end].replace('mh_attention_fused_fp8_out(','mh_attention_fused_fp8_out_pdl(')+',const uint*pf,uint pt,uint*of){';body=fn[sig_end+2:-3]
    # wait after the line that computes win/head (third line of the body)
    lines=body.split('\n');k=[i for i,l in enumerate(lines) if 'win=wh/heads' in l];assert len(k)==1,lines[:5]
    lines.insert(k[0]+1,' '+wait);body='\n'.join(lines)
    return ['\n'+attr+sig+body+'\n '+pub+'\n}\n']
emit('multihead_fused_attention.hip',['HIP_ISA_HALF 1','HIP_MH_RTZ_ISA 1'],mhfused_twins,'multihead_fused_attention.generated.hip')
# mh reference: shift_pack hand-written twin (per-element early returns in the original)
def mh_twins(s):
    return ['''
KERNEL void mh_shift_pack_pdl(const float* input,float* output,uint width,uint height,uint work_width,uint work_height,uint pad_x,uint pad_y,uint channels,uint plain_short_y,const uint*pf,uint pt,uint pww,uint psx,uint psy,uint*of){
 uint i=lane();const bool ok=valid_spatial(channels)&&i<work_width*work_height*channels;
 const uint pg=(__builtin_amdgcn_workgroup_id_x()*256u)/channels; /* 256 elements per group = a fraction of one token at C512 */
 if(pf){uint tid=__builtin_amdgcn_workitem_id_x();int xg=int(pg%work_width)-int(pad_x),yg=int(pg/work_width)-int(pad_y);
  if(tid==0&&xg>=0&&yg>=0&&xg<int(width)&&yg<int(height)){uint idx=((uint(yg)+psy)*pww+uint(xg)+psx)/16;while(__hip_atomic_load(pf+idx,__ATOMIC_RELAXED,__HIP_MEMORY_SCOPE_AGENT)<pt)__builtin_amdgcn_s_sleep(1);}
  __builtin_amdgcn_s_barrier();}
 if(ok){uint p=i/channels,c=i%channels;int x=int(p%work_width)-int(pad_x),y=int(p/work_width)-int(pad_y);if(plain_short_y&&channels==256&&height==4)y=(y%4+4)%4;
  output[i]=(x<0||y<0||x>=int(width)||y>=int(height))?0.f:input[(uint(y)*width+uint(x))*channels+c];}
 pdl512_pub(of,pg/16);
}
''']
emit('multihead_reference.hip',['HIP_ISA_HALF 1','HIP_PDL_KERNELS 1'],mh_twins,'multihead-reference.generated.hip')

# host
shutil.rmtree(out/'Development',ignore_errors=True);(out/'Development/HIP').mkdir(parents=True)
for p in (root/'Development/HIP').glob('*.h'):shutil.copyfile(p,out/'Development/HIP'/p.name)
p=out/'Development/HIP/hip_reference_network.h';h=p.read_text()
def rep(old,new,count=1):
    global h;assert h.count(old)==count,(old[:70],h.count(old));h=h.replace(old,new)
rep('static constexpr unsigned PDL_SLOTS=16384,PDL_RING=64;','static constexpr unsigned PDL_SLOTS=16384,PDL_RING=96;\n struct PdlCur{unsigned*flags=nullptr;unsigned target=0;}pdl512_cur;unsigned pdl512_mask=[]{const char*e=std::getenv("DLSS5_PDL512_STAGES");return e?unsigned(std::stoul(e)):127u;}();\n unsigned*PdlOut(unsigned kind,unsigned c,unsigned ww,unsigned hh,unsigned contrib){return PdlSlot(kind,c,ww,hh,contrib);}')
rep(' public: unsigned PdlCalls()const{return pdl_calls;} private:',' public: unsigned PdlCalls()const{return pdl_calls;} void SetPairMode(unsigned m){static std::vector<unsigned>t=[]{std::vector<unsigned>v{0,15,7,8};if(const char*e=std::getenv("DLSS5_PDL_TABLE")){v.clear();std::string x=e;size_t i=0;while(i<=x.size()){size_t j=x.find(\',\',i);if(j==std::string::npos)j=x.size();v.push_back(unsigned(std::stoul(x.substr(i,j-i))));i=j+1;}}return v;}();pdl_mode=t.at(m);pdl_calls=0;} unsigned PairCalls()const{return pdl_calls;} private:')
# Run: strip _pdl for shape rules, launch by full name
rep('  U count=Count(n),threads=256;unsigned groups=0;std::string module=m,kernel=name;','  U count=Count(n),threads=256;unsigned groups=0;std::string module=m,kernel=name;const std::string full_kernel=kernel;const bool pdl_twin=kernel.size()>4&&kernel.compare(kernel.size()-4,4,"_pdl")==0;if(pdl_twin)kernel.resize(kernel.size()-4);')
rep('if(pdl_anyorder){++pdl_calls;api.Check(ext_launch(Fn(module,kernel),','if(pdl_anyorder){++pdl_calls;api.Check(ext_launch(Fn(module,pdl_twin?full_kernel:kernel),')
rep('else api.Check(api.hipModuleLaunchKernel(Fn(module,kernel),gg,1,1,threads,1,1,0,stream,argv,nullptr),name);}','else api.Check(api.hipModuleLaunchKernel(Fn(module,pdl_twin?full_kernel:kernel),gg,1,1,threads,1,1,0,stream,argv,nullptr),name);}')
# the deep alias rule sets kernel=name (full name): keep the stripped one
rep('   module="deep_fast";kernel=name;threads=32;groups=0;','   module="deep_fast";threads=32;groups=0;')
# Body: shift_pack
rep('if(!identity&&!mapped)Run("mh","mh_shift_pack",size_t(n)*c,P(input),P(packed),w,h,ww,hh,sx,sy,c,U(0));',
'''const bool pdl512=(pdl_mode&8)&&c==512&&opt.split_mix_h16w&&opt.split_ffn_fused&&opt.c512_proj_tiles&&opt.c512_qkv_frag&&!opt.split_mix_fused&&opt.fp8_av&&opt.fused_mh&&n%16==0;pdl512_cur={};
 if(!identity&&!mapped){if(pdl512){const bool head=!pdl_prev.flags;unsigned*of=PdlOut(2,c,ww,hh,256);unsigned ot=pdl_last_target;const unsigned*pf=head?nullptr:pdl_prev.flags;unsigned pt=head?0u:pdl_prev.epoch,pww=head?16u:pdl_prev.ww,psx=head?0u:pdl_prev.sx,psy=head?0u:pdl_prev.sy;
   pdl_anyorder=!head&&(pdl512_mask&1);Run("mh","mh_shift_pack_pdl",size_t(n)*c,P(input),P(packed),w,h,ww,hh,sx,sy,c,U(0),pf,pt,pww,psx,psy,of);pdl_anyorder=false;pdl512_cur={of,ot};}
  else Run("mh","mh_shift_pack",size_t(n)*c,P(input),P(packed),w,h,ww,hh,sx,sy,c,U(0));}
 else if(pdl512&&identity&&pdl_prev.flags)pdl512_cur={pdl_prev.flags,pdl_prev.epoch};''')
rep('Run("deep","split_mix_blocked_h16w",size_t(n)*512,P(packed),PackedSplitFfnWeightMixHalf(Block(block,"ffwd")),P(mixed),n);',
'''if(pdl512){unsigned*of=PdlOut(3,c,ww,hh,8);unsigned ot=pdl_last_target;pdl_anyorder=pdl512_cur.flags!=nullptr&&(pdl512_mask&2);Run("deep","split_mix_blocked_h16w_pdl",size_t(n)*512,P(packed),PackedSplitFfnWeightMixHalf(Block(block,"ffwd")),P(mixed),n,(const unsigned*)pdl512_cur.flags,pdl512_cur.target,of);pdl_anyorder=false;pdl512_cur={of,ot};}else Run("deep","split_mix_blocked_h16w",size_t(n)*512,P(packed),PackedSplitFfnWeightMixHalf(Block(block,"ffwd")),P(mixed),n);''')
rep('Run("deep","split_ffn_fused_fp8_t8",size_t(n)*512,P(mixed),opt.split_mix_h16w?PackedSplitFfnWeightMixHalf(Block(block,"ffwd")):PackedSplitFfnWeight(Block(block,"ffwd")),P(contract),P(contract8),n);',
'''if(pdl512){unsigned*of=PdlOut(4,c,ww,hh,32);unsigned ot=pdl_last_target;pdl_anyorder=(pdl512_mask&4)!=0;Run("deep","split_ffn_fused_fp8_t8_pdl",size_t(n)*512,P(mixed),PackedSplitFfnWeightMixHalf(Block(block,"ffwd")),P(contract),P(contract8),n,(const unsigned*)pdl512_cur.flags,pdl512_cur.target,of);pdl_anyorder=false;pdl512_cur={of,ot};}else Run("deep","split_ffn_fused_fp8_t8",size_t(n)*512,P(mixed),opt.split_mix_h16w?PackedSplitFfnWeightMixHalf(Block(block,"ffwd")):PackedSplitFfnWeight(Block(block,"ffwd")),P(contract),P(contract8),n);''')
rep('if(opt.c512_proj_tiles)Run("deep","split_projection_frag",size_t(n)*512,P(contract8),PackedSplitProjectionFrag(Block(block,"ffwd-projection")),P(packed),P(ffn),P(ffn8),n);',
'''if(pdl512){unsigned*of=PdlOut(5,c,ww,hh,8);unsigned ot=pdl_last_target;pdl_anyorder=(pdl512_mask&8)!=0;Run("deep","split_projection_frag_pdl",size_t(n)*512,P(contract8),PackedSplitProjectionFrag(Block(block,"ffwd-projection")),P(packed),P(ffn),P(ffn8),n,(const unsigned*)pdl512_cur.flags,pdl512_cur.target,of);pdl_anyorder=false;pdl512_cur={of,ot};}else if(opt.c512_proj_tiles)Run("deep","split_projection_frag",size_t(n)*512,P(contract8),PackedSplitProjectionFrag(Block(block,"ffwd-projection")),P(packed),P(ffn),P(ffn8),n);''')
rep('Run("mh_fast","mh_qkv_normalize_frag_c512",size_t(n)*1536,P(ffn8),PackedMhWeightQkvFrag(Block(block,"attention"),512),P(producer_norm),n);}',
'''if(pdl512){unsigned*of=PdlOut(6,c,ww,hh,24);unsigned ot=pdl_last_target;pdl_anyorder=(pdl512_mask&16)!=0;Run("mh_fast","mh_qkv_normalize_frag_c512_pdl",size_t(n)*1536,P(ffn8),PackedMhWeightQkvFrag(Block(block,"attention"),512),P(producer_norm),n,(const unsigned*)pdl512_cur.flags,pdl512_cur.target,of);pdl_anyorder=false;pdl512_cur={of,ot};pdl_ffn_flags=of;pdl_ffn_epoch=ot;pdl_keep.push_back(mixed);pdl_keep.push_back(contract8);pdl_keep.push_back(ffn8);pdl_keep.push_back(packed);}else Run("mh_fast","mh_qkv_normalize_frag_c512",size_t(n)*1536,P(ffn8),PackedMhWeightQkvFrag(Block(block,"attention"),512),P(producer_norm),n);}''')
# AttentionFast c512: fused attention + projection
rep('if(opt.fused_mh){Run("mh_fused",opt.fp8_av?"mh_attention_fused_fp8_out":opt.fp8_normalized?"mh_attention_fused_fp8":"mh_attention_fused",size_t(windows)*heads,P(norm),weights,P(av),w,h,c);norm.reset();}',
'''if(opt.fused_mh){if(c==512&&pdl_ffn_flags&&opt.fp8_av&&(pdl_mode&8)){unsigned*of=PdlOut(7,c,w,h,128);unsigned ot=pdl_last_target;pdl_anyorder=(pdl512_mask&32)!=0;Run("mh_fused","mh_attention_fused_fp8_out_pdl",size_t(windows)*heads,P(norm),weights,P(av),w,h,c,(const unsigned*)pdl_ffn_flags,pdl_ffn_epoch,of);pdl_anyorder=false;pdl512_cur={of,ot};}
   else{pdl512_cur={};Run("mh_fused",opt.fp8_av?"mh_attention_fused_fp8_out":opt.fp8_normalized?"mh_attention_fused_fp8":"mh_attention_fused",size_t(windows)*heads,P(norm),weights,P(av),w,h,c);}norm.reset();}''')
rep('if(cropw)if(opt.c512_proj_frag&&c==512)Run("mh_fast","mh_attention_project_frag_c512",size_t(n)*c,P(av),P(input),PackedMhWeightQkvFrag(aw,512),P(out),n,U(raw?3:0),cropw,croph,w,sx,sy);',
'''if(cropw)if(opt.c512_proj_frag&&c==512){if(pdl512_cur.flags){unsigned*of=PdlOut(8,c,w,h,8);unsigned ot=pdl_last_target;pdl_anyorder=(pdl512_mask&64)!=0;Run("mh_fast","mh_attention_project_frag_c512_pdl",size_t(n)*c,P(av),P(input),PackedMhWeightQkvFrag(aw,512),P(out),n,U(raw?3:0),cropw,croph,w,sx,sy,(const unsigned*)pdl512_cur.flags,pdl512_cur.target,of);pdl_anyorder=false;pdl_prev={of,ot,w,sx,sy};pdl512_cur={};pdl_ffn_flags=nullptr;pdl_keep.push_back(av);}
   else{pdl_prev={};Run("mh_fast","mh_attention_project_frag_c512",size_t(n)*c,P(av),P(input),PackedMhWeightQkvFrag(aw,512),P(out),n,U(raw?3:0),cropw,croph,w,sx,sy);}}''')
rep(' if(opt.pdl){if(opt.graph)throw std::runtime_error("pdl requires graph off");api.Load(ext_launch,"hipExtModuleLaunchKernel");',' if(true){if(opt.graph)throw std::runtime_error("pdl requires graph off");api.Load(ext_launch,"hipExtModuleLaunchKernel");')
p.write_text(h)
x=(root/'src/native_hip_network.h').read_text();a=x.index('hip_reference::Options o;');b=x.index('  const wchar_t*modules=',a)
opts=x[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift','o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)','o.assets=argv[1]')
r=(root/'Development/HIP/experiments/vit-schedule-cause/runner.cpp.in').read_text()
a=r.index(' for(unsigned frame=0;');b=r.index('api.hipFree(x);',a)
r=r[:a]+(here/'timing.inc').read_text()+r[b:]
(out/'network.cpp').write_text(r.replace('/* OPTIONS */',opts).replace('PASS ViT schedule controls','PASS pdl c512'))
print('written',out)
