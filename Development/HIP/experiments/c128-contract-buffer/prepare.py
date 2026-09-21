from pathlib import Path
import difflib
root=Path(__file__).resolve().parents[4];old=(root/'hip/multihead_fast_padded.hip').read_text();s=old
start=s.index('DEV void mh_ffn_qkv_body');prefix=s[:start];body=s[start:]
needle=' __attribute__((shared)) unsigned char qfeature[16*(C+4)];';assert body.count(needle)==1
body=body.replace(needle,needle+'\n __attribute__((shared)) unsigned char contract_buffer[C==128?16*(C+4):1];')
needle=''' if constexpr(Project){
  __builtin_amdgcn_s_barrier();
  for(uint e=0;e<8;e++)hidden[(group*8+e)*(C+4)+wave*16+rc]=''';assert body.count(needle)==1
body=body.replace(needle,''' if constexpr(Project){
  // C128 contraction output has separate storage, so it cannot overwrite unread expansion inputs.
  unsigned char*project_input=C==128?contract_buffer:hidden;
  if constexpr(C!=128)__builtin_amdgcn_s_barrier();
  for(uint e=0;e<8;e++)project_input[(group*8+e)*(C+4)+wave*16+rc]=''')
needle='__builtin_memcpy(&a,hidden+rc*(C+4)+k+group*8,8);uint off=8*C*C';assert body.count(needle)==1
body=body.replace(needle,'__builtin_memcpy(&a,project_input+rc*(C+4)+k+group*8,8);uint off=8*C*C')
s=prefix+body;out=Path('/tmp/c128-contract-buffer');out.mkdir(exist_ok=True);(out/'multihead_fast_padded.hip').write_text(s)
(root/'Development/HIP/experiments/c128-contract-buffer/candidate.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='a/hip/multihead_fast_padded.hip',tofile='b/hip/multihead_fast_padded.hip')))
