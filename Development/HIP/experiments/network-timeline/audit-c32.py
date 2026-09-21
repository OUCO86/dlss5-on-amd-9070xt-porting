"""Use only an assembly artifact whose sibling HSACO matches the timed module hash."""
from pathlib import Path
import re,json,sys
s=Path(sys.argv[1]).read_text();out={}
for name in ['c32_fast_ffn_attention_fused_half_prefix_finish_main8','c32_fast_ffn_attention_fused_half_chain','c32_post_merge_head_half']:
 a=s.index('\n'+name+':');b=s.index('\n',s.index('; Occupancy:',a));t=s[a:b]
 ops=re.findall(r'(?:^\s*|::\s*)([sv]_[a-zA-Z0-9_]+|global_[a-zA-Z0-9_]+|ds_[a-zA-Z0-9_]+)',t,re.M)
 arith=lambda op:op.startswith('v_') and '_f32' in op and '_cvt_' not in op and not op.startswith(('v_wmma_','v_cmp'))
 row={'wmma_static_ops':sum(op.startswith('v_wmma_') for op in ops),'single_f32_arithmetic_static_ops':sum(arith(op) and not op.startswith('v_dual_') for op in ops),'dual_f32_arithmetic_static_ops':sum(arith(op) and op.startswith('v_dual_') for op in ops),'conversion_static_ops':sum('_cvt_' in op for op in ops),'lds_static_ops':sum(op.startswith('ds_') for op in ops),'global_load_static_ops':sum(op.startswith('global_load_') for op in ops)}
 for k in ['NumVgprs','NumVGPRsForWavesPerEU','LDSByteSize','Occupancy','ScratchSize']:
  m=re.search(r'; '+k+r':\s*(\d+)',t);row[k]=int(m[1]) if m else None
 out[name]=row
Path(sys.argv[2]).write_text(json.dumps({'timed_and_assembly_sibling_hsaco_sha256':'C381FCE5BB69927D8A33EBDD1ED2B083E4621BF504095CA3202E081034DFD67D','warning':'Static ops are not executed counts, clock shares, or a dual-issue eligibility ratio.','kernels':out},indent=2)+'\n');print(json.dumps(out,indent=2))
