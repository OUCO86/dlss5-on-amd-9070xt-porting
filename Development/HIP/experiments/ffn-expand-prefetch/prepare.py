from pathlib import Path
import difflib
root=Path(__file__).resolve().parents[4];old=(root/'hip/multihead_fast_padded.hip').read_text();s=old
start=s.index(' f8 expand[4]{};',s.index('DEV void mh_ffn_qkv_body'));a=s.index('  for(uint tile=0;tile<4;tile++){uint row=',start);b=s.index('\n',a);line=s[a:b]
needle='expand[tile]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,expand[tile]);'
assert needle in line
loads=line.replace(needle,'weight_fragments[tile]=b;')
replacement='''  if constexpr(C==128||C==256){i2 weight_fragments[4];
'''+loads+'''
  for(uint tile=0;tile<4;tile++)expand[tile]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,weight_fragments[tile],expand[tile]);
  }else{
'''+line+'\n  }'
s=s[:a]+replacement+s[b:];out=Path('/tmp/ffn-expand-prefetch');out.mkdir(exist_ok=True);(out/'multihead_fast_padded.hip').write_text(s)
(root/'Development/HIP/experiments/ffn-expand-prefetch/candidate.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='a/hip/multihead_fast_padded.hip',tofile='b/hip/multihead_fast_padded.hip')))
