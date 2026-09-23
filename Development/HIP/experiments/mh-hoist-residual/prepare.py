# Hoist the residual feature loads of the fused attention kernels to kernel entry. The c256 phase ledger charged
# "residual/diag" 21% of the wave: the two/four 8-byte feature fragments per lane are loaded right after the final
# attention sync, cold, and the diagonal-WMMA chain waits on them. Loading them at entry (8 VGPRs for c256, 4 for
# c64/c128) overlaps that latency with the attention batches. Same bytes -> bit-exact. Module-set host.
#   pair1: c256 body only     pair2: c64 + c128 + c256     pair3 = pair1
from pathlib import Path
import shutil
here=Path(__file__).resolve().parent; root=here.parents[3]; out=Path('/tmp/mh-hoist-residual')
for sub in ('pair1','pair2','pair3'): shutil.rmtree(out/sub, ignore_errors=True); (out/sub).mkdir(parents=True)
s0=(root/'hip/multihead_fused_attention.hip').read_text()
def patch(s,entry,C,nfrag,ct_expr,load_old):
    assert s.count(entry)==1,(entry[:60],s.count(entry))
    hoist=entry+f' i2 hf[{nfrag}];if constexpr(ByteFeature&&Diag){{uint p=raster(win,first+rc(),width);for(uint f=0;f<{nfrag};f++){{uint ct={ct_expr};__builtin_memcpy(&hf[f],feature8+p*{C}+ct*16+gr()*8,8);}}}}\n'
    s=s.replace(entry,hoist,1)
    assert s.count(load_old)==1,(load_old[:60],s.count(load_old)); return s
E64=' uint alltid=__builtin_amdgcn_workitem_id_x(),head=alltid/128,tid=alltid%128,wave=tid/32,first=wave*16;\n const uint channels=64;\n' if False else None
# entries: the line after each body's `channels=` constant is the alltid line; anchor on the exact alltid line + following raster/LDS line uniqueness
ENT256=' uint alltid=__builtin_amdgcn_workitem_id_x(),localhead=alltid/128,tid=alltid%128,wave=tid/32,first=wave*16;\n'
L256='i2 a{};if constexpr(ByteFeature)__builtin_memcpy(&a,feature8+p*256+ct*16+gr()*8,8);else'
s1=patch(s0,ENT256,256,4,'localhead*4+f',L256).replace(L256,'i2 a{};if constexpr(ByteFeature)a=hf[pair*2+j];else',1)
# c64 and c128 share the alltid line text; split the file at the c128 template to patch each once
i=s1.index('template<bool ByteFeature,bool ByteOut,bool Diag=false>\nDEV void c128_attention_project_body')
ENT=' uint alltid=__builtin_amdgcn_workitem_id_x(),head=alltid/128,tid=alltid%128,wave=tid/32,first=wave*16;\n'
L64='i2 a{};if constexpr(ByteFeature)__builtin_memcpy(&a,feature8+p*64+ct*16+gr()*8,8);else'
L128='i2 a{};if constexpr(ByteFeature)__builtin_memcpy(&a,feature8+p*128+ct*16+gr()*8,8);else'
a=patch(s1[:i],ENT,64,2,'head*2+f',L64).replace(L64,'i2 a{};if constexpr(ByteFeature)a=hf[j];else',1)
b=patch(s1[i:],ENT,128,2,'head*2+f',L128).replace(L128,'i2 a{};if constexpr(ByteFeature)a=hf[j];else',1)
s2=a+b
for m,s in {1:s1,2:s2,3:s1}.items():
    (out/f'pair{m}'/'multihead_fused_attention.generated.hip').write_text('#define HIP_ISA_HALF 1\n#define HIP_MH_RTZ_ISA 1\n'+s+'\n')
print('written; pair2 extra lines:',sum(1 for x,y in zip(s1.split('\n'),s2.split('\n')) if x!=y))
