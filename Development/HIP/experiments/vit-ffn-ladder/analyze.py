from pathlib import Path
import csv,json,re,sys
root=Path(sys.argv[1]);asm=Path(sys.argv[2]).read_text();result={};isa={}
for match in re.finditer(r'^((?:vit_|ladder_)\w+):',asm,re.M):
 name=match[1];end=asm.find('; COMPUTE_PGM_RSRC2',match.end());part=asm[match.start():end]
 isa[name]={key:int(re.search(r'; '+key+r': (\d+)',part)[1]) for key in ('NumVgprs','ScratchSize','LDSByteSize','Occupancy')}
(root/'isa.json').write_text(json.dumps(isa,indent=2)+'\n')
for d in sorted(root.iterdir()):
 if not d.is_dir() or not re.fullmatch(r'(900|1080)-(expand|contract)',d.name):continue
 rows=list(csv.DictReader((d/'ladder.csv').open()));assert len(rows)==(24 if 'expand' in d.name else 16)
 assert all(int(x['output_diff'])==int(x['raw_diff'])==0 and float(x['mean_us'])>0 for x in rows)
 assert (d/'run.log').read_text().count('bitdiff=0')==2
 variants={}
 for name in sorted(set(x['variant'] for x in rows)):
  r=[x for x in rows if x['variant']==name];base=[float(x['mean_us']) for x in r if int(x['slot'])%4 in (0,3)];test=[float(x['mean_us']) for x in r if int(x['slot'])%4 in (1,2)]
  b=sum(base)/4;t=sum(test)/4;tokens=int(r[0]['tokens']);ops=2*tokens*1024*4096
  variants[name]={'baseline_us':b,'candidate_us':t,'delta_us':t-b,'principal_matrix_tflops':ops/t/1e6,'baseline_tflops':ops/b/1e6,'tokens':tokens,'base_slots':base,'test_slots':test}
 result[d.name]=variants
assert len(result)==4
(root/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
lines=['# ViT FFN 真实尺寸台阶\n','基线 8bca0f7，直接截取 block31 的真实输入和权重，900/1080 对应 M=400/640。展开 K1024/N4096，收缩 K4096/N1024。每方案两轮 ABBA；输出验证放计时外。\n','| 案例 | 方案 | 完整算子 μs | 方案 μs | 差 μs | 主矩阵有效 TFLOPS |\n|---|---|---:|---:|---:|---:|']
for case,variants in result.items():
 for name,v in variants.items():lines.append(f"| {case} | {name} | {v['baseline_us']:.3f} | {v['candidate_us']:.3f} | {v['delta_us']:+.3f} | {v['principal_matrix_tflops']:.2f} |")
lines+=['''
## 方案含义与局限

- expand/raw：原矩阵遍历，写 FP32 累加结果；无激活/FP8 编码。
- expand/act：同矩阵及原激活，写 FP32 激活结果；无 FP8 编码。
- expand/split：raw + 单独激活/编码核，计时包含两次启动及中间 FP32 读写。
- contract/raw：保留原残差初始化及四段 K1024 累加顺序，仅取消最后 F(H(...))，写 FP32；因此不是完全裸 GEMM。
- contract/split：raw + 单独 F(H(...)) 核；与完整算子相同 FP32 输出。

raw/act 每个候选计时槽后补做相应尾部，再对完整算子逐字节比较；raw 本身另作重复确定性检查，不声称独立 CPU FP32 GEMM 参考验证。全 80 个槽位通过，8 次首尾原始网络 FP32 检查通过。双架构编译，仅 gfx1201 实跑。

展开 raw/act 输出比生产 FP8 输出大四倍，因此差值同时包含写流量、编译调度/寄存器变化；不能相减解释为纯激活成本。都是热重复，不能将单核微秒乘调用次数代替网络计时。有效 TFLOPS 仅计主矩阵 FLOPs，分母包含访存和其他操作，不是硬件利用率。

本批无需生产修改，保留完整 CSV、hash 与资源数据。''']
(root/'README.md').write_text('\n'.join(lines)+'\n')
print(json.dumps(result,indent=2))
