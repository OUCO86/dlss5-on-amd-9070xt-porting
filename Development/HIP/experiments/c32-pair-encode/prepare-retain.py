from pathlib import Path
import re
here=Path(__file__).resolve().parent;root=here.parents[3];out=Path('/tmp/c32-pair-encode')
s=(root/'hip/c32_fused_ffn_attention.hip').read_text()
a=s.index('template<bool HalfOutput,bool Mapped=false');b=s.index('\nKERNEL ',a)
body=s[a:b];needle='float v=Hrtz(acc[ci][e]);saved_ffn[ci][e]=(_Float16)v;ffn8[(first+gr()*8+e)*36+ci*16+rc()]=static_cast<unsigned char>(fp8(v));'
assert body.count(needle)==1
body=body.replace(needle,'float v;uint byte;_Float16 half;retain_encode(acc[ci][e],half,v,byte);saved_ffn[ci][e]=half;ffn8[(first+gr()*8+e)*36+ci*16+rc()]=static_cast<unsigned char>(byte);').replace('c32_fused_body(','c32_retain_body(',1)
code='#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n'+s+'\n'+(here/'retain.inc').read_text()+'\n'+body+'\n'
for name in re.findall(r'^void (c32_\w+)\(',s[b:],re.M):
 line=next(x for x in s[b:].splitlines() if x.startswith('void '+name+'('))
 code+='KERNEL __attribute__((amdgpu_flat_work_group_size(128,128))) C32_OCC\n'+line.replace('void '+name+'(',f'void {name}_pair4(',1).replace('c32_fused_body<','c32_retain_body<')+'\n'
(out/'retain.hip').write_text(code)
s=(out/'network.cpp').read_text().replace('for(unsigned test=1;test<=3;test++)','for(unsigned test=4;test<=4;test++)')
assert 'test=4' in s
(out/'network-retain.cpp').write_text(s)
