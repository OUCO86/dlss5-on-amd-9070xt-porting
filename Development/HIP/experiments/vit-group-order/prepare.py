"""Real ViT expand: small grouped-M task ordering, unchanged one-wave groups."""
from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = Path('/tmp/vit-group-order')
OUT.mkdir(exist_ok=True)


def rep(text, old, new):
    assert text.count(old) == 1, (old[:80], text.count(old))
    return text.replace(old, new, 1)


source = (ROOT / 'hip/deep_fast.hip').read_text()
a = source.index('template<bool Tiled=false,bool ByteInput=false,bool Frag=false,bool TiledInput=false>')
b = source.index('\n// BM token tiles per wave', a)
body = source[a:b]
variant = rep(body, 'bool TiledInput=false>', 'bool TiledInput=false,uint GM=1>')
variant = rep(variant, 'vit_expand_blocked_body(', 'vit_expand_order_body(')
variant = rep(variant,
    ' uint tiles=outputs/64,first=bid()/tiles*16,col=bid()%tiles*64;if(first>=tokens)return;',
    ''' uint tiles=outputs/64,rows=(tokens+15)/16,id=bid(),group=id/(GM*tiles),within=id%(GM*tiles);
 uint base=group*GM,left=rows-base,local_m,local_n;
 if(left>=GM){local_m=within%GM;local_n=within/GM;}
 else{local_m=within%left;local_n=within/left;}
 uint first=(base+local_m)*16,col=local_n*64;if(first>=tokens)return;''')
code = '#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_BRANCHLESS_F 1\n' + source + '\n' + variant
entry = next(x for x in source.splitlines() if x.startswith('WAVE void vit_expand_blocked_fp8_frag_bytein('))
code += '\n' + entry.replace('vit_expand_blocked_fp8_frag_bytein(', 'vit_expand_blocked_fp8_frag_bytein_order1(', 1) + '\n'
for mode, gm in [(2, 2), (3, 4), (4, 8)]:
    line = entry.replace('vit_expand_blocked_fp8_frag_bytein(', f'vit_expand_blocked_fp8_frag_bytein_order{mode}(', 1)
    line = line.replace('vit_expand_blocked_body<true,true,true>', f'vit_expand_order_body<true,true,true,false,{gm}>')
    code += line + '\n'
a = source.index('template<bool Partial,bool Tiled=false,bool ByteStream=false,bool HalfOut=false,bool Frag=false>')
b = source.index('\n// Fragment-weight twin', a)
contract = source[a:b]
contract = rep(contract, 'bool Frag=false>', 'bool Frag=false,uint GM=1>')
contract = rep(contract, 'vit_contract_blocked_body(', 'vit_contract_order_body(')
contract = rep(contract,
    ' uint blocks=tokens,part0=Partial?bid()/blocks:0,local=Partial?bid()%blocks:bid(),first=local/16*16,col=local%16*64;',
    ''' uint blocks=tokens,part0=Partial?bid()/blocks:0,id=Partial?bid()%blocks:bid();
 uint rows=(tokens+15)/16,group=id/(GM*16),within=id%(GM*16),base=group*GM,left=rows-base,local_m,local_n;
 if(left>=GM){local_m=within%GM;local_n=within/GM;}
 else{local_m=within%left;local_n=within/left;}
 uint first=(base+local_m)*16,col=local_n*64;''')
code += '\n' + contract
contract_entry = next(x for x in source.splitlines() if x.startswith('WAVE void vit_contract_blocked_fp8_frag('))
code += '\n' + contract_entry.replace('vit_contract_blocked_fp8_frag(', 'vit_contract_blocked_fp8_frag_order1(', 1) + '\n'
for mode, gm in [(5, 2), (6, 4), (7, 8)]:
    line = contract_entry.replace('vit_contract_blocked_fp8_frag(', f'vit_contract_blocked_fp8_frag_order{mode}(', 1)
    line = line.replace('vit_contract_blocked_body<false,false,false,false,true>', f'vit_contract_order_body<false,false,false,false,true,{gm}>')
    code += line + '\n'
(OUT / 'kernel.hip').write_text(code)

(OUT / 'Development/HIP').mkdir(parents=True, exist_ok=True)
for path in (ROOT / 'Development/HIP').glob('*.h'):
    shutil.copyfile(path, OUT / 'Development/HIP' / path.name)
p = OUT / 'Development/HIP/hip_reference_network.h'
h = rep(p.read_text(), 'class Network {', 'class Network {\n unsigned order_mode=0,order_calls=0;')
h = rep(h, ' Handle Fn(const std::string&m,const std::string&name){', ''' Handle Fn(const std::string&m,const std::string&original){
 std::string name=original;
 if(m=="deep_fast"&&original=="vit_expand_blocked_fp8_frag_bytein"){
  ++order_calls;if(order_mode>=1&&order_mode<=4)name+="_order"+std::to_string(order_mode);
 }
 if(m=="deep_fast"&&original=="vit_contract_blocked_fp8_frag"){
  ++order_calls;if(order_mode==1||order_mode>=5)name+="_order"+std::to_string(order_mode);
 }
''')
h = rep(h, ' Handle Stream()const{return stream;}', ''' void SetOrderMode(unsigned m){if(m>7)throw std::runtime_error("order mode");Synchronize();order_mode=m;order_calls=0;}
 unsigned OrderCalls()const{return order_calls;}
 Handle Stream()const{return stream;}''')
p.write_text(h)
native = (ROOT / 'src/native_hip_network.h').read_text()
a = native.index('hip_reference::Options o;'); b = native.index('  const wchar_t*modules=', a)
options = native[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift', 'o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)', 'o.assets=argv[1]')
runner = (HERE.parent / 'c32-post-input/runner.cpp.in').read_text()
runner = runner.replace('SetPostMode', 'SetOrderMode').replace('PostCalls', 'OrderCalls').replace('post_calls', 'target_calls').replace('POST_INPUT_CANDIDATES', 'VIT_ORDER_CANDIDATES')
runner = runner.replace('calls!=frames', 'calls!=frames*16').replace('post must execute exactly once per frame', 'expand+contract must execute exactly sixteen times per frame').replace('PASS post input controls', 'PASS ViT order controls')
runner = runner.replace('m>4', 'm>7').replace('candidate must be 1..4', 'candidate must be 1..7')
(OUT / 'network.cpp').write_text(runner.replace('/* OPTIONS */', options))
for name in ('build.ps1', 'run.ps1', 'start.ps1'):
    shutil.copyfile(HERE / name, OUT / name)
(OUT / 'source-manifest.json').write_text(json.dumps({
    'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
    'host_sha256': hashlib.sha256((ROOT / 'Development/HIP/hip_reference_network.h').read_bytes()).hexdigest(),
    'runner_template_sha256': hashlib.sha256((HERE.parent / 'c32-post-input/runner.cpp.in').read_bytes()).hexdigest(),
    'modes': {'0': 'production', '1': 'identical control', '2': 'expand GM2', '3': 'expand GM4', '4': 'expand GM8', '5': 'contract GM2', '6': 'contract GM4', '7': 'contract GM8'},
}, indent=2)+'\n')
print(OUT)
