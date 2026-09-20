"""Generate an isolated approximate attention candidate; never edit hip/deep_fast.hip."""
from pathlib import Path
import difflib
root=Path(__file__).resolve().parents[4]
s=(root/'hip/deep_fast.hip').read_text()
a=s.index('template<uint MAXT,bool ByteInput=false,bool ByteOut=false>\nDEV void vit_attention_fused_body')
b=s.index('// Byte-stream twins:',a)
f=s[a:b]
f=f.replace('__attribute__((shared)) unsigned char p8[16*(MAXT+16)];','__attribute__((shared)) unsigned char p8[16*(MAXT/2+32)];')
f=f.replace('const uint S=tokens+16;', 'const uint KT=tokens/2,S=((KT+15)&~15u)+16;')
f=f.replace('key<tokens;key+=16','key<KT;key+=16').replace('k<tokens;k+=16','k<KT;k+=16')
old='if constexpr(ByteInput)__builtin_memcpy(&y,in8+(tokens+key+rc())*1024+head*32+k+gr()*8,8);else for(uint e=0;e<8;e++){uint j=k+gr()*8+e;pack(y,e,in[(tokens+key+rc())*1024+head*32+j]);}'
new='for(uint e=0;e<8;e++){uint j=k+gr()*8+e;pack(y,e,vit_pair_value<ByteInput>(in,1,2*(key+rc()),head*32+j,tokens));}'
assert old in f;f=f.replace(old,new)
f=f.replace('t[(gr()*8+e)*24+rc()]=(unsigned short)(((hb<<4)+0x4000u)&65535u);','t[(gr()*8+e)*24+rc()]=key+rc()<KT?(unsigned short)(((hb<<4)+0x4000u)&65535u):0;')
old='if constexpr(ByteInput){uint b=in8[(2*tokens+key)*1024+head*32+c*16+rc()];y[e/4]=int(uint(y[e/4])|(b<<(8*(e%4))));}else pack(y,e,in[(2*tokens+key)*1024+head*32+c*16+rc()]);'
assert old in f;f=f.replace(old,'pack(y,e,vit_pair_value<ByteInput>(in,2,2*key,head*32+c*16+rc(),tokens));')
helper='''// Approximation experiment: adjacent K/V centroid pairs, all Q unchanged.
// Equal pair multiplicity cancels between attention numerator and denominator.
// Only an experiment; no assertion of mathematical equivalence or visual safety.
template<bool ByteInput> DEV float vit_pair_value(const float*in,uint part,uint token,uint c,uint tokens){
 token=token+1<tokens?token:tokens-2;uint i=(part*tokens+token)*1024+c;
 if constexpr(ByteInput){const unsigned char*p=reinterpret_cast<const unsigned char*>(in);return .5f*(__builtin_amdgcn_cvt_f32_fp8(p[i],0)+__builtin_amdgcn_cvt_f32_fp8(p[i+1024],0));}
 else return .5f*(in[i]+in[i+1024]);
}
'''
new=s[:a]+helper+f+s[b:]
out=Path('/tmp/vit-kv-pair-src');out.mkdir(exist_ok=True);(out/'deep_fast.hip').write_text(new)
Path(__file__).with_name('candidate.patch').write_text(''.join(difflib.unified_diff(s.splitlines(True),new.splitlines(True),fromfile='a/hip/deep_fast.hip',tofile='b/hip/deep_fast.hip')))
print(out)
