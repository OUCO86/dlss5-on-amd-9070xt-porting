from pathlib import Path
import re,collections,json,sys
out=Path(sys.argv[3]);out.mkdir(parents=True,exist_ok=True);rows=[]
for file,name in [(sys.argv[1],'c32_post_merge_head_half'),(sys.argv[2],'mh_ffn_fused_c128_project_mapped_g128_qkv_bytein_fb'),(sys.argv[2],'mh_ffn_fused_c256_frag_project_mapped_g128_qkv_bytein_fb')]:
 s=Path(file).read_text();a=s.index('\n'+name+':');b=s.index('.Lfunc_end',a);ops=collections.Counter(re.findall(r'^\s+((?:s_|v_|ds_|global_|flat_|scratch_|buffer_)\w+)\b',s[a:b],re.M))
 m=re.search(r'\.amdhsa_kernel '+name+r'\n(.*?)\.end_amdhsa_kernel',s,re.S);assert m
 resources=dict(re.findall(r'\.(amdhsa_(?:group_segment_fixed_size|private_segment_fixed_size|next_free_vgpr|next_free_sgpr))\s+(\d+)',m[1]))
 rows.append(dict(name=name,static_instructions=sum(ops.values()),static_wmma=sum(v for k,v in ops.items() if 'wmma' in k),wait_opcode_occurrences=sum(v for k,v in ops.items() if 'wait' in k),resources=resources,opcodes=dict(ops)))
(out/'static-isa.json').write_text(json.dumps(rows,indent=2)+'\n')
# Additional issued-matrix work omitted from principal FLOPs model. Not a complete dynamic ISA count.
root=Path(__file__).resolve().parents[4];old=json.loads((root/'Development/results/9070-theoretical-20260921/estimate.json').read_text());extras={}
for tier,W,H,n in [('900',1600,960,400),('1080',1920,1152,640)]:
 s=old[tier]['stages_GFLOP'];t32=s['C32/fp8']*1e9/(2*(12*32*32+128*32))
 fp16=t32*4096 # Q/K norm32 terms and probability norm64, each replicated to16 matrix columns
 fp8=0
 for c in [64,128,256]:
  t=s[f'C{c}/fp8']*1e9/(2*(9*c*c+256*c));fp16+=t*64*c;fp8+=t*96*c # local attention denominator; three16x16 diagonal residual products
 t512=s['C512/fp16']*1e9/(2*(512*512+8*64*256));fp16+=t512*64*512
 fp16+=8*2*32*n*n*16 # ViT denominator as ones-matrix product
 chain=sum((W//2+(8 if sh&1 else 0))*(H//2+(8 if sh&2 else 0)) for sh in [3,1,2])*2
 fp8+=chain*2*3*32*32
 # Inline prefix executes K32 with half of K zero, versus logical K16 in old estimate.
 fp16+=W*H*16*32*2
 extra_ms=fp8/389e12*1e3+fp16/195e12*1e3
 extras[tier]=dict(additional_fp8_GFLOP=fp8/1e9,additional_fp16_GFLOP=fp16/1e9,additional_advertised_peak_budget_ms=extra_ms,principal_plus_known_extra_budget_ms=old[tier]['optimistic_matrix_ms']+extra_ms)
(out/'matrix-overhead-addendum.json').write_text(json.dumps(extras,indent=2)+'\n');print(json.dumps(extras,indent=2))
