# C32 残差：跳过全零 K16 半块

来自当前 C32 阶段账的残差初始化调查。`AppendC32ResidualDiagonals` 为每个 part/列半块/K半块准备16×16矩阵；列半块 ci 只在 K半块 kt=ci 有非零对角，kt!=ci 全零。原核仍执行两者。

候选把 `for kt=0..1` 改成 `kt=ci`，保留 part 顺序和所有非零乘加。三个 part × 两列半块，共少六条 WMMA。只影响 block2/3/4/67/68/69 的 mode3 残差路径。

**等价验证**：独立GPU核用六组真实权重，对每通道覆盖全部有限 E4M3 编码（含正负零），比较原12条与候选6条结果的float32位模式；每组8192个结果、六组合计49152个结果。NaN编码不在结论范围内（探针将其映射为±448，有限编码仍全部覆盖）。这是针对有限FP8生产数据域的检查，不是一般浮点“乘零随便删”的规则。

`prepare.py` 生成原核、同体异名 control、删零候选；按现行prod8选项跑两档整网ABBA，每帧确认六个目标调用命中、槽首尾RGB逐位比较。`inspect.py` 确认原核和control机器码一致，以及 WMMA 静态条数56→50、VGPR不变。

`start.ps1` 编译并跑筛选；`run.ps1 -Frames 800 -Repeats 2 -Label confirm` 拉长计时。`build-candidate.ps1` 生成使用标准导出名的独立候选模块（gfx1201/gfx1200），不改生产目录。`regression.ps1 -CorrectnessOnly` / `-ExtraControls` 复用既有NativeGameFrame回放，基线和候选均PDL=1，基线固定prod8。

性能、双架构构建与回归的实际状态见 `Development/results/c32-diag-zero-20260925/README.md`，不以这个操作说明代替完成记录。
