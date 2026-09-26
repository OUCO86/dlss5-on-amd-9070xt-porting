"""Generate isolated post70 staging experiments from current production sources."""
from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = Path('/tmp/c32-post-input')
OUT.mkdir(exist_ok=True)


def replace_once(text, old, new):
    assert text.count(old) == 1, (old[:90], text.count(old))
    return text.replace(old, new, 1)


source = (ROOT / 'hip/c32_fused_ffn_attention.hip').read_text()
start = source.index('template<bool HalfOutput,bool Mapped=false')
end = source.index('\nKERNEL ', start)
body = source[start:end]
declaration = '   const uint c0=(l&7)*4;float sc[4],sh[4];'
load = '__builtin_memcpy(&q,raw_input+idx2+c0,16);'

# Each wave covers two adjacent image rows. With even height and shift 0/4,
# both rows have identical validity and y/2. k=2,3 reuse k=0,1 bit for bit.
# Keep the original load for any geometry outside that proven condition.
reuse = replace_once(body, declaration, declaration + '\n   f4 low_saved[2];')
reuse = replace_once(reuse, load, '''if(k<2 || (sy&1u) || (sourceh&1u)){
     __builtin_memcpy(&q,raw_input+idx2+c0,16);
     if(k<2)low_saved[k]=q;
    }else q=low_saved[k-2];''')

reuse_even = replace_once(reuse, 'if(k<2 || (sy&1u) || (sourceh&1u)){', 'if(k<2){')
half_low = replace_once(body, load, '''_Float16 qh[4];__builtin_memcpy(qh,reinterpret_cast<const _Float16*>(raw_input)+idx2+c0,8);
    _Pragma("unroll") for(uint e=0;e<4;e++)q[e]=float(qh[e]);''')
half_low = replace_once(half_low, 'else main[i]=v;', 'else reinterpret_cast<_Float16*>(main)[i]=(_Float16)v;')
# Control is an identical body under a distinct symbol. No synthetic values.
code = '#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_C32_DIAG_WEIGHTS 1\n' + source
entry = next(line for line in source[end:].splitlines()
             if line.startswith('void c32_post_merge_head_half('))
for suffix, variant in [('control', body), ('reuse', reuse), ('reuse_even', reuse_even)]:
    code += '\n' + variant.replace('c32_fused_body(', f'post_{suffix}_body(', 1)
    code += '\nKERNEL __attribute__((amdgpu_flat_work_group_size(128,128))) C32_OCC\n'
    code += entry.replace('c32_post_merge_head_half(', f'c32_post_merge_head_half_{suffix}(', 1).replace('c32_fused_body<', f'post_{suffix}_body<') + '\n'
code += '\n' + half_low.replace('c32_fused_body(', 'post_half_low_body(', 1)
for name in ('c32_post_merge_head_half', 'c32_fast_ffn_attention_fused_half_chain_finish'):
    line = next(x for x in source[end:].splitlines() if x.startswith('void '+name+'('))
    code += '\nKERNEL __attribute__((amdgpu_flat_work_group_size(128,128))) C32_OCC\n'
    code += line.replace('void '+name+'(', 'void '+name+'_half_low(', 1).replace('c32_fused_body<', 'post_half_low_body<')+'\n'
(OUT / 'kernel.hip').write_text(code)

(OUT / 'Development/HIP').mkdir(parents=True, exist_ok=True)
for path in (ROOT / 'Development/HIP').glob('*.h'):
    shutil.copyfile(path, OUT / 'Development/HIP' / path.name)
header_path = OUT / 'Development/HIP/hip_reference_network.h'
header = header_path.read_text()
header = replace_once(header, 'class Network {', 'class Network {\n unsigned post_mode=0,post_calls=0;')
header = replace_once(header, ' Handle Fn(const std::string&m,const std::string&name){', ''' Handle Fn(const std::string&m,const std::string&original){
 std::string name=original;
 if(m=="c32_fused_ffn" && original=="c32_post_merge_head_half"){
  ++post_calls;if(post_mode==1)name+="_control";if(post_mode==2)name+="_reuse";if(post_mode==3)name+="_reuse_even";if(post_mode==4)name+="_half_low";
 }
 if(m=="c32_fused_ffn" && original=="c32_fast_ffn_attention_fused_half_chain_finish" && post_mode==4)name+="_half_low";
''')
header = replace_once(header, ' Handle Stream()const{return stream;}', ''' void SetPostMode(unsigned m){if(m>4)throw std::runtime_error("post mode");if(m==3&&(opt.height%2||opt.post_shift>3))throw std::runtime_error("reuse_even geometry");if(m==4&&(!opt.down_crop_fused||!opt.raw_chain||!opt.c32_finish_fused||!opt.post_merge_fold||!opt.post_head_fused||opt.skip_blocks.count(69)))throw std::runtime_error("half_low requires production chain69->post70");Synchronize();post_mode=m;post_calls=0;}
 unsigned PostCalls()const{return post_calls;}
 Handle Stream()const{return stream;}''')
header_path.write_text(header)

host = (ROOT / 'src/native_hip_network.h').read_text()
a = host.index('hip_reference::Options o;')
b = host.index('  const wchar_t*modules=', a)
options = host[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift', 'o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)', 'o.assets=argv[1]')
runner = (HERE / 'runner.cpp.in').read_text().replace('/* OPTIONS */', options)
(OUT / 'network.cpp').write_text(runner)
for name in ('build.ps1', 'run.ps1', 'start.ps1'):
    shutil.copyfile(HERE / name, OUT / name)
(OUT / 'source-manifest.json').write_text(json.dumps({
    'source': str(ROOT / 'hip/c32_fused_ffn_attention.hip'),
    'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
    'host_sha256': hashlib.sha256((ROOT / 'Development/HIP/hip_reference_network.h').read_bytes()).hexdigest(),
    'modes': {'0': 'production', '1': 'identical control', '2': 'reuse vertical low-resolution input', '3': 'reuse with even-geometry specialization', '4': 'FP16 block69 main -> post70 low'},
}, indent=2) + '\n')
print(OUT)
