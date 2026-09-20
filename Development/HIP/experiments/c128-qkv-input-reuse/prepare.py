from pathlib import Path
import difflib
root=Path(__file__).resolve().parents[4];old=(root/'hip/multihead_fast_padded.hip').read_text();s=old
needle='  }else\n  for(uint part=0;part<3;part++){f8 q{};';assert s.count(needle)==1
s=s.replace(needle,'''  }else{
  i2 cached_input[C==128?8:1];
  if constexpr(C==128)for(uint k=0;k<C;k+=16)__builtin_memcpy(&cached_input[k/16],qfeature+rc*(C+4)+k+group*8,8);
  for(uint part=0;part<3;part++){f8 q{};''')
start=s.index('  i2 cached_input');a=s.index('__builtin_memcpy(&a,qfeature+rc*(C+4)+k+group*8,8);',start)
s=s[:a]+s[a:].replace('__builtin_memcpy(&a,qfeature+rc*(C+4)+k+group*8,8);','if constexpr(C==128)a=cached_input[k/16];else __builtin_memcpy(&a,qfeature+rc*(C+4)+k+group*8,8);',1)
# close the added else scope immediately before the function ends
end=s.index('\n }else{\n for(uint e=',start);s=s[:end]+'\n }'+s[end:]
out=Path('/tmp/c128-qkv-input-reuse');out.mkdir(exist_ok=True);(out/'multihead_fast_padded.hip').write_text(s)
(root/'Development/HIP/experiments/c128-qkv-input-reuse/candidate.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='a/hip/multihead_fast_padded.hip',tofile='b/hip/multihead_fast_padded.hip')))
