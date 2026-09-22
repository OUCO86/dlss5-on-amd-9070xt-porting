from pathlib import Path
import shutil, re

here = Path(__file__).resolve().parent
root = here.parents[3]
out = Path('/tmp/c32-pair-encode')
out.mkdir(exist_ok=True)
s = (root/'hip/c32_fused_ffn_attention.hip').read_text()
a = s.index('template<bool HalfOutput,bool Mapped=false')
b = s.index('\nKERNEL ', a)
body = s[a:b]
begin = body.index(' for(uint ci=0;ci<2;ci++)for(uint e=0;e<8;e++){\n#if HIP_C32_REGISTER_FFN')
end = body.index('\n sync_window();\n // A single raw QKV', begin)
helpers = (here/'encode.inc').read_text()
code = '#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n' + s + '\n' + helpers
names = re.findall(r'^void (c32_\w+)\(', s[b:], re.M)
for mode in (1, 2, 3):
    replacement = '''
#if !HIP_C32_REGISTER_FFN
#error pair encoding requires register FFN
#endif
 for(uint ci=0;ci<2;ci++)for(uint e=0;e<8;e+=2){
  float a,b;uint bytes;pair_encode<MODE>(acc[ci][e],acc[ci][e+1],a,b,bytes);
  saved_ffn[ci][e]=(_Float16)a;saved_ffn[ci][e+1]=(_Float16)b;
  ffn8[(first+gr()*8+e)*36+ci*16+rc()]=static_cast<unsigned char>(bytes);
  ffn8[(first+gr()*8+e+1)*36+ci*16+rc()]=static_cast<unsigned char>(bytes>>8);
 }
'''.replace('MODE', str(mode))
    variant = (body[:begin]+replacement+body[end:]).replace('c32_fused_body(', f'c32_pair{mode}_body(', 1)
    code += '\n' + variant + '\n'
    for name in names:
        line = next(x for x in s[b:].splitlines() if x.startswith('void '+name+'('))
        code += 'KERNEL __attribute__((amdgpu_flat_work_group_size(128,128))) C32_OCC\n'
        code += line.replace('void '+name+'(', f'void {name}_pair{mode}(', 1).replace('c32_fused_body<',f'c32_pair{mode}_body<')+'\n'
code += (here/'primitive.inc').read_text()
(out/'kernel.hip').write_text(code)
(out/'Development/HIP').mkdir(parents=True, exist_ok=True)
for p in (root/'Development/HIP').glob('*.h'):
    shutil.copyfile(p, out/'Development/HIP'/p.name)
p = out/'Development/HIP/hip_reference_network.h'
s = p.read_text().replace('class Network {', 'class Network {\n unsigned pair_mode=0,pair_calls=0;\n',1)
old='for(unsigned repeat=0;repeat<repeats_here;repeat++)api.Check(api.hipModuleLaunchKernel(Fn(module,kernel),groups?groups:(count+255ull)/256,1,1,threads,1,1,0,stream,argv,nullptr),name);'
assert s.count(old)==1
s=s.replace(old, 'if(module=="c32_fused_ffn"){++pair_calls;if(pair_mode)kernel+="_pair"+std::to_string(pair_mode);}\n  '+old,1)
s=s.replace(' Handle Stream()const{return stream;}', ' void SetPairMode(unsigned m){pair_mode=m;pair_calls=0;} unsigned PairCalls()const{return pair_calls;}\n Handle Stream()const{return stream;}',1)
p.write_text(s)
x=(root/'src/native_hip_network.h').read_text();a=x.index('hip_reference::Options o;');b=x.index('  const wchar_t*modules=',a)
opts=x[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift','o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)','o.assets=argv[1]')
s=(root/'Development/HIP/experiments/vit-schedule-cause/runner.cpp.in').read_text()
a=s.index(' for(unsigned frame=0;');b=s.index('api.hipFree(x);',a)
s=s[:a]+(here/'timing.inc').read_text()+s[b:]
(out/'network.cpp').write_text(s.replace('/* OPTIONS */',opts).replace('PASS ViT schedule controls','PASS C32 paired encoding'))
