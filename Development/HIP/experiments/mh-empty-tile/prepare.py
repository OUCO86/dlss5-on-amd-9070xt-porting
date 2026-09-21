from pathlib import Path
import subprocess,shutil,difflib
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent;out=Path('/tmp/mh-empty-tile');out.mkdir(exist_ok=True)
source=subprocess.check_output(['git','show','147421f:hip/multihead_fast_padded.hip'],cwd=root,text=True)
needle='if constexpr(C==128&&Mapped){';assert source.count(needle)==1
for name,predicate in [('c64','(C==64||C==128)'),('c256','(C==128||C==256)')]:
 s=source.replace(needle,f'if constexpr({predicate}&&Mapped){{',1)
 (out/(name+'.hip')).write_text('#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_FFN_HOIST_RES 2\n'+s)
 (here/(name+'.patch')).write_text(''.join(difflib.unified_diff(source.splitlines(True),s.splitlines(True),fromfile='a/hip/multihead_fast_padded.hip',tofile='b/hip/multihead_fast_padded.hip')))
shutil.copytree(root/'src',out/'src',dirs_exist_ok=True);(out/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (root/'Development/HIP').glob('*.h'):shutil.copyfile(p,out/'Development/HIP'/p.name)
helper=root/'Development/HIP/experiments/kernel-bottleneck/prepare-pure.py';s=helper.read_text().replace("out=Path('/tmp/kernel-bottleneck')", "out=Path('/tmp/mh-empty-tile')")
exec(compile(s,str(helper),'exec'),{'__file__':str(helper)})
p=out/'Development/HIP/hip_reference_network.h';s=p.read_text().replace('class Network {','class Network {\n bool empty_tile_timed=false;',1)
needle='for(unsigned repeat=0;repeat<repeats_here;repeat++)api.Check(';assert s.count(needle)==1
inject='''if(!empty_tile_timed){if(const char*target=std::getenv("DLSS5_EMPTY_TARGET");target&&kernel==target){
 empty_tile_timed=true;auto fn=Fn(module,kernel);auto launch=[&](){api.Check(api.hipModuleLaunchKernel(fn,groups,1,1,threads,1,1,0,stream,argv,nullptr),"empty tile timing");};
 api.Check(api.hipStreamSynchronize(stream),"drain");for(unsigned i=0;i<2000;i++)launch();api.Check(api.hipStreamSynchronize(stream),"warmup");
 auto begin=std::chrono::steady_clock::now();for(unsigned i=0;i<10000;i++)launch();api.Check(api.hipStreamSynchronize(stream),"complete");
 double us=std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-begin).count()/10000;
 printf("EMPTY_TILE kernel=%s groups=%u threads=%u us=%.6f\\n",kernel.c_str(),groups,threads,us);fflush(stdout);
 }}
'''
s=s.replace(needle,inject+needle,1);p.write_text(s)
# Require the requested kernel to have been visited (rather than silently timing no target).
s=p.read_text().replace(' void Stage(', ' public: bool EmptyTileTimed()const{return empty_tile_timed;}\n private:\n void Stage(',1);p.write_text(s)
p=out/'pure.cpp';s=p.read_text();s=s.replace('api.hipFree(x);api.hipFree(y);return errors?1:0;', 'if(!net.EmptyTileTimed())throw std::runtime_error("target kernel not reached");api.hipFree(x);api.hipFree(y);return errors?1:0;');p.write_text(s)
