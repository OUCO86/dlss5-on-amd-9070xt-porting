from pathlib import Path
root=Path(__file__).resolve().parents[4];s=(root/'hip/multihead_fast_padded.hip').read_text()
# Keep duplicate outputs live to compiler; memory clobber prevents reusing the first pass's loads.
def wrap(text,begin,end,init,result,decl=''):
 a=text.index(begin,text.index('DEV void mh_ffn_qkv_body'));b=text.index(end,a);body=text[a:b]
 if decl:body=body.replace(decl,init)
 else:body=init+'\n'+body
 opaque=''.join('asm volatile("" : : "v"('+v+') : "memory");' for v in result)
 return text[:a]+(''+(decl if decl else '')+'\nfor(uint probe_repeat=0;probe_repeat<((C==128||C==256)?2u:1u);probe_repeat++){if constexpr(C==128||C==256)asm volatile("" : : : "memory");\n'+body+'\nif constexpr(C==128||C==256){'+opaque+'}\n}\n')+text[b:]
out=Path('/tmp/ffn-stage-cost');out.mkdir(exist_ok=True)
# Stage-specific independent modules; original production never edited.
variants={}
variants['expand']=wrap(s,' for(uint k=0;k<C;k+=16){i2 a{};','\n#if HIP_FFN_COOP_INPUT\n // ByteIn','for(uint q=0;q<4;q++)expand[q]=f8{};', [f'expand[{q}][{e}]' for q in range(4) for e in range(8)])
variants['contract']=wrap(s,' for(uint k=first_k;k<last_k;k+=16)','\n if constexpr(Project)','accum=f8{};',[f'accum[{e}]' for e in range(8)])
# Projection matrix alone: save initialized residual and restart each duplicate from it.
a=s.index('  for(uint k=0;k<C;k+=16){i2 a,b;__builtin_memcpy(&a,hidden+rc*(C+4)',s.index('DEV void mh_ffn_qkv_body'))
t=s[:a]+'  f8 probe_initial=result;\n'+s[a:]
variants['project']=wrap(t,'  for(uint k=0;k<C;k+=16){i2 a,b;__builtin_memcpy(&a,hidden+rc*(C+4)','\n  for(uint e=0;e<8;e++){uint byte=','result=probe_initial;',[f'result[{e}]' for e in range(8)])
# Non-BatchNorm production QKV path: duplicate each dot product, normalize once.
a=s.index('  for(uint part=0;part<3;part++){f8 q{};',s.index('DEV void mh_ffn_qkv_body'))
p=s[:a];tail=s[a:];begin='   for(uint k=0;k<C;k+=16){i2 a,b;__builtin_memcpy(&a,qfeature';i=tail.index(begin);j=tail.index('\n   if(part<2)',i)
body=tail[i:j];tail=tail[:i]+'for(uint probe_repeat=0;probe_repeat<((C==128||C==256)?2u:1u);probe_repeat++){q=f8{};if constexpr(C==128||C==256)asm volatile("" : : : "memory");'+body+'if constexpr(C==128||C==256){'+''.join('asm volatile("" : : "v"(q['+str(e)+']) : "memory");' for e in range(8))+'}}'+tail[j:];variants['qkv']=p+tail
for name,code in variants.items():(out/(name+'.hip')).write_text('#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_FFN_HOIST_RES 2\n'+code)
