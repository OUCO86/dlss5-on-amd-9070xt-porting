from pathlib import Path
import difflib
root=Path(__file__).resolve().parents[4];p=root/'hip/c32_fused_ffn_attention.hip';old=p.read_text();s=old
needle='else if constexpr(RawMapped)c=F(lv[j]);';assert s.count(needle)==1;s=s.replace(needle,'else if constexpr(RawMapped)c=lv[j];')
needle='packed[row*36+l]=static_cast<unsigned char>(fp8(v));';assert s.count(needle)==2
replacement='uint packed_v=fp8(v);if constexpr(RawMapped&&!Merge)if((bits(v)&0x7fffffffu)==0)packed_v=0;packed[row*36+l]=static_cast<unsigned char>(packed_v);'
s=s.replace(needle,replacement,1)
out=Path('/tmp/c32-single-pack');out.mkdir(exist_ok=True);(out/'c32_fused_ffn_attention.hip').write_text(s+'''
WAVE void check_single_pack(uint*out){uint i=bid()*32+__builtin_amdgcn_workitem_id_x();if(i>=65536)return;float x=from_half(i);uint old=fp8(F(x)),now=fp8(x);if((bits(x)&0x7fffffffu)==0)now=0;out[i]=(old==now)?0u:((old<<8)|now|0x10000u);}
''')
(root/'Development/HIP/experiments/c32-single-pack/candidate.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='a/hip/c32_fused_ffn_attention.hip',tofile='b/hip/c32_fused_ffn_attention.hip')))
print(out)
