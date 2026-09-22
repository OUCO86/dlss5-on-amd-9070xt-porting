# 给 Hikari：算力缺口研究交接（2026-09-22 20:34）

用户目标：先找“必要成本”与可避免成本，再尝试优化；318是研究锚点，不是优化更新日志。当前研究提交c9f6739，main；没有未部署的生产改动。不要覆盖正在运行的游戏DLL。

## 先校准刚才的判断

1. **300TF不是已证硬上限。** 密度探针的299TF是特定读取/额外独立矩阵工作、频率和调度下的结果，不证明剩余25%必然丢失。同规模寄存器供数四链已测338TF；它也不等于真实带全量读取核的上限。未获得可直接套用的RDNA4精确L0服务峰值，ROCm某些cache roofline表明确是RDNA3.5启发式，不可据此封账。
2. **150→300不能全记成可回收排队。** 探针变更包括计算密度、独立链、资源/指令组织；没有证明真实原核存在一倍可回收空间。此前已说明逻辑读取字节、缓存请求覆盖与DRAM流量是三种口径。
3. **必要的算法操作，不等于当前实现的必要周期。** 转换、激活、归一化确实有功能，但冗余转换可以删除、发射可能重叠；不能把当前非WMMA指令全部标成不可回收。
4. **234次调用不能乘几微秒就得到不可回收0.5～1ms。** 主机提交与GPU执行可能重叠，Graph/融合/队列改变也可能回收；密集逐核事件曾额外加约10ms，计时探针必须校准。
5. **C32已开账，静态指令也数过。** 指令比例只能定调查方向，不能决定35%耗时里多少必要。要区分真实分支/循环次数、FP8/FP16 WMMA、VALU/VMEM/LDS/标量、依赖和重叠；wait指令的条数不是等待周期。
6. **一次LDS试验不能给所有“可回收空间”封账。** 只能评价该方案；需核查旧实验，分开B驻留、已有hidden/attention LDS、单/双缓冲与组大小变化。新增LDS复制/同步/容量压力必须计入。我们未把B权重驻留双缓冲作为已验证结论。

## C32汇编具体位置

当前会话本地已下载：
- `/tmp/c32-pair-encode/kernel.s`：生产基线导出和pair1/2/3实验导出。
- `/tmp/c32-pair-encode/retain.s`：生产基线导出和pair4保留half位元实验。

**读没有 `_pairN` 后缀的导出作为基线**：
- `c32_fast_ffn_attention_fused_half_prefix_finish_main8`
- `c32_fast_ffn_attention_fused_half_chain`
- `c32_post_merge_head_half`

9070 Windows持久副本（SSH别名amd9070）：
`D:\DLSSNR-Lab\hip-backend\c32-pair-encode\modules\c32_fused_ffn_attention-packed.hsaco.s`
以及`modules-retain`下同名文件。生产源：`hip/c32_fused_ffn_attention.hip`。

已存的静态统计：
- `Development/results/instruction-audit-20260921/static-isa.json`
- `Development/results/c32-pair-encode-20260922/isa.json`（补有实际NumVgprs与驻留声明两个口径）
- 分析脚本：`Development/HIP/experiments/instruction-audit/analyze.py`、`c32-pair-encode/analyze.py`

| 基线导出 | 静态指令 | 静态WMMA | NumVgprs实际 | next_free_vgpr声明 | LDS bytes |
|---|---:|---:|---:|---:|---:|
| prefix |3327|74|153|169|15360|
| chain |3603|70|177|177|15360|
| post/head |3013|58|158|217|19712|

**217不是post的实际寄存器数。** 编译器Occupancy/分配声明/HIP驻留上限也不是动态占用率。静态计数含控制流，WMMA还有不同精度；不要算“58/3013=矩阵时间占比”。

## C32已有证据，避免从头重复

- `results/c32-phase-cost-20260921/`：FFN、编码、QKV、分数、归一化、AV、投影；576槽，24次整网原始FP32同。探针一次就可能改变调度，packv仍有约4～9%扰动，不能把重复增量相加成阶段饼图。
- `results/c32-edge-cost-20260921/`：输入映射/合并/暂存与finish/RGB尾部；120槽、12次原始输出同，含同步/资源扰动。
- `results/instruction-audit-20260921/matrix-overhead-addendum.json`：补数归一化等实际发出的冗余矩阵工作；只补这项仍不足解释总差距。
- `results/kernel-bottleneck-20260921/report.md`：纯HIP热重复捕获C32 post的memory busy99.056%、stalled5.461%、L0hit71.619%、L2hit96.188%。与ViT高stalled并不同，不能照搬ViT机制。混合D3D/HIP捕获曾破坏输出，该批被撤回。
- `results/c32-pair-encode-20260922/`：RTZ/FP8配对没稳定收益；保留原RTZ half位元确实每核少16次转换，整网仍无稳定变化。没证明所有转换免费。
- 去掉post half暂存/重读残差以前更慢；no-unroll降VGPR却退化、盲删barrier曾破坏逐位。详情先rg DevHistory。

以上相对目录均在Development下。

## 最新ViT认识

总入口：`Development/results/network-cost-summary-20260921/README.md`。
文章：`/home/lmxxf/work/ai-theorys-study/wechat/318.md`。

- 整网历史约12.86/18.30ms；整个ViT约1.488/2.471ms，即约12～14%，展开只是其中部分。这不是“已解释比例”。C32约35%。
- 已解释一项明确不对称：展开约56→36μs来自固定尺寸后的循环/读取调度；反向禁止收缩展开又显著变慢。相关生产改动早已合入。
- 真实ViT展开热捕获：L0hit57.826%、L2hit99.947%、memory stalled68.404%，原始网络输出同。支持供数背压，不等于整网68%的时间或矩阵空闲。
- 源码逐指令128B区域账与实核262144000次L0请求完全吻合。每次实核逻辑读200MiB、读请求覆盖480MiB、含尾部500MiB；这些不是实际搬运量，更不是500MiB DRAM。
- 同布局权重读取64→128位，L0请求少33.31%，L2只少8.97%；删的主要是L0命中请求，不能期待总时间减半。数值校验用非均匀CPU参考。
- 相同工作集、地址和计算，地址低位/逻辑任务映射/组组织可改变耗时；没有命名具体bank或调度器。固定wave数后W1→W2约29.5→43μs，静态HIP上限都64wave/MP；uniform化没有解除慢点。
- 同机器码、W1不变，仅置换任务编号，约29.4→40.7μs；热捕获L2请求108789776→123859662。捕获与独立计时状态不同，不能把13.85%请求增量当时间份额。

最新四组报告：`wmma-page-gap-20260922`、`wmma-width-gap-20260922`、`wmma-groups-gap-20260922`、`wmma-pitch-gap-20260922`（均results下）。

## 下一步建议

优先回C32大头，用已有ISA/真实执行路径及请求账本补“必要功能工作、实现额外工作、服务/等待”的区分；不要再从零只数一遍指令就封账。ViT LDS驻留可作明确假说的实验，但需匹配组大小/逻辑wave映射对照，原数据说明仅分组本身就能改变十余μs。

测量纪律：独立微测显存曾降到约190MHz，正式组用计时外D2D+chunk维持约2505MHz，ADL只读。短HIP事件出现过非正值，批量wall/sync为主。RGP只用输出通过的纯HIP；百分比要看分母，不与无profile时间拼周期份额。COMGR双架构gfx1200/gfx1201编译，实跑仅gfx1201。讨论/推断写报告，DevHistory只记已做工作，阶段commit。
