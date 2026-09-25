# C32 对角残差删零：很小的逐位收益，已完成候选验证

2026-09-25，Yami。基线prod8，RX9070XT/gfx1201。**900长槽约−0.026ms（约0.2%），1080约−0.015ms（约0.09%）**。收益小，保留为下次合包候选；生产源码、游戏安装和0.30发布包未改，不宣称游戏FPS已有可见变化。

## 改了什么

FFN残差被拆成三个FP8对角矩阵。原来每个16列半块都遍历两个K16半块，其中一个全零。候选保留 `kt=ci` 的非零半块，省下六条WMMA和对应取数，非零乘加顺序不变。

只选择三个已计时核：half_chain、half_chain_finish_dcrop、half_chain_finish，对应block2/3/4/67/68/69。标准导出候选保留其余七个核的原机器码，三个目标核与实测孪生候选逐字节一致（`standard-function-check.json`）。不把改整个模板后额外变化的prefix/mapped机器码顺带带入。

## 性能对照

同进程原核/同体异名control/候选，PDL=1、adaptive/graph/dup关，计时内无读回；每槽首尾RGB逐位同。每帧六个目标调用确实命中。

| | 900 B−A ms | 1080 B−A ms |
|---|---|---|
| 每槽160帧，三轮 | −0.02504 / −0.00158 / −0.02151 | −0.01943 / −0.02513 / −0.03589 |
| 每槽800帧，确认两轮 | −0.02282 / −0.02841 | −0.02104 / −0.00856 |
| 长槽均值 | **−0.02562** | **−0.01480** |
| 同期control长槽均值 | +0.00688 | +0.00471 |

十组候选配对均快，但量级只有百分之零点一左右；不要把短槽的−0.027ms当成1080固定收益。没有用跨批绝对时间拼提速，也没有把12帧正确性回放里的计时当性能证据。

## 正确性与资格验证

- 独立GPU核：六组真实残差权重，每通道覆盖全部有限E4M3编码（包括正负零），原12次WMMA与候选6次的float32位模式合计49,152项全同。NaN编码不属于验证域。
- 原核与control函数体逐字节一致；候选三个核静态WMMA条数56→50，VGPR分别151/153/153不变（`isa.json`）。
- 标准导出候选双架构COMGR编译通过。gfx1201实测；gfx1200仅编译，仍无9060实机结论。
- NativeGameFrame正式回放与prod8逐帧比较：900/1080各静态与移动两序列；额外720移动、900历史、900浮点输入、900浮点特征，共8种条件，每种12帧，**96个候选RGB帧与基线全部同哈希**。基线与候选都PDL=1。
- 每帧哈希与最终模块SHA见`validation.json`，正常和额外回放日志分别为`regression.log`、`extra-controls.log`。

## 候选位置与复现

工具 `../../HIP/experiments/c32-diag-zero/`：prepare→build-candidate→regression（CorrectnessOnly与ExtraControls）→collect。生成源码在 `/tmp/c32-diag-zero/candidate.hip`，由已入库生成脚本从当前生产源构建，不依赖手改二进制。

靶机候选：`D:\DLSSNR-Lab\hip-backend\c32-diag-zero\candidate-modules`（prod8其余模块 + 新C32）；`candidate-gfx1200` 只放替换用的C32模块。候选未装游戏。

- gfx1201 C32 SHA256：`e41c5c0bcb91235b5a6842fc67f09ee86c53e232fad8b3cafaa4a7f8146dac08`
- gfx1200 C32 SHA256：`fafe5fe1213b333f3a2fdfdd2c7420bfdeb5423849d7e8e4dd5517edcd273fe2`
- 配对实验模块 SHA256：`60abada31e21f7b7e63475d1d9a433eddad4ac1cf51bc0a744f7285ec981022a`

`results-*` 保存短槽，`results-*confirm` 保存长槽；`analyze.py` 可复算。后续若生产源变动，须重新生成并核验，不能直接沿用本轮hash或收益。
