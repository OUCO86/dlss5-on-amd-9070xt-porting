from pathlib import Path
import csv,json,re,sys
root=Path(sys.argv[1]);asm=Path(sys.argv[2]).read_text();result={};isa={}
for match in re.finditer(r'^(c32_\w+):',asm,re.M):
 name=match[1];end=asm.find('; COMPUTE_PGM_RSRC2',match.end());part=asm[match.start():end]
 isa[name]={key:int(re.search(r'; '+key+r': (\d+)',part)[1]) for key in ('NumVgprs','ScratchSize','LDSByteSize','Occupancy')}
(root/'isa.json').write_text(json.dumps(isa,indent=2)+'\n')
for d in sorted(root.iterdir()):
 if not d.is_dir() or not re.fullmatch(r'(900|1080)-(prefix|chain|post)',d.name):continue
 rows=list(csv.DictReader((d/'phase.csv').open()));assert len(rows)==(12 if 'chain' in d.name else 24)
 assert all(int(x['byte_diff'])==0 and float(x['mean_us'])>0 for x in rows)
 assert (d/'run.log').read_text().count('bitdiff=0')==2
 phases={}
 for phase in sorted(set(x['phase'] for x in rows)):
  v=[]
  for c in range(3):
   a=[float(x['mean_us']) for x in rows if int(x['comparison'])==c and x['phase']==phase];assert len(a)==4
   base=(a[0]+a[3])/2;test=(a[1]+a[2])/2;v.append(dict(base_us=base,test_us=test,delta_us=test-base))
  phases[phase]={'comparisons':v,'calibration_percent':100*v[0]['delta_us']/v[0]['base_us']}
 result[d.name]=phases
assert len(result)==6
(root/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
for phase in ('input','tail'):
 lines=[f'# C32 {phase} 独立测量\n','基线 8bca0f7；900/1080 实际输入，gfx1201。每项原核/探针一次、一次/两次、一次/四次分别 ABBA。\n','| 案例 | N=1 校准变化 | 多一遍 μs | 多三遍 / 3 μs |\n|---|---:|---:|---:|']
 for name,phases in result.items():
  if phase not in phases:continue
  x=phases[phase];lines.append(f"| {name} | {x['calibration_percent']:+.2f}% | {x['comparisons'][1]['delta_us']:.3f} | {x['comparisons'][2]['delta_us']/3:.3f} |")
 lines+=['\n所有槽位完整输出逐位相同，每案例首尾整网 FP32 相同。增量是热重复成本，不能作原生时间占比或与其他阶段相加。']
 if phase=='input':lines+=['输入包含 prefix 的输入构造与前置 FP16 投影；chain 的映射读取/格式转换；post 的低高分辨率合并/暂存。每轮加统一工作组同步，增量包含同步及循环开销；prefix 累加器每轮归零。不是纯读取带宽测量。prefix VGPR 153→179，仍需考虑调度扰动。']
 else:lines+=['prefix 尾部包含 main8 存储和下采样；post 包含 RGB 三个点积、颜色融合及写出。chain 无独立 finish/head，不测空尾部。prefix N=1 比原核稍快也属于生成代码/漂移差异，不能当生产优化。RGB 多三遍的单位增量低于多一遍，已保留非线性，不强行拟合单一阶段耗时。']
 (root/(phase+'.md')).write_text('\n'.join(lines)+'\n')
print('120 slots, 12 raw network checks passed')
