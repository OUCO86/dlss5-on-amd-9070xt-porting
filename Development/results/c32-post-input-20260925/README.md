# post70 输入：三种逐位候选均未取得可用收益

2026-09-25 22:21 起，Yami，RX 9070 XT / gfx1201。Zero 已明确授权本项目编译和实验由 agent 自行执行。本轮只用独立实验目录，未改生产源、游戏安装或发布包。

## 结论

原计划的“mapped/post 尚有 16 次窄读”已过时，生产源已是 4 次 b128。先测更小的 post 输入改法：消除纵向重复读取、去掉回落分支的特化、block69→post70 用 FP16 传值。**均保持本轮 RGB 槽首尾逐位一致，但没有稳定整网提速，不采用。**

这否定的是三个具体候选，不能推出整个 staging 已无优化空间，也不把 null 归因成某个确定的硬件瓶颈。

## 同批 ABBA（B−A，正数为变慢）

每候选每档 3 组 ABBA，每槽预热 20 帧、计时 160 帧。表中均值仅作汇总，判断同时看三次配对和同体异名 control。

| 候选 | 900 三次差值 ms | 900 均值 | 1080 三次差值 ms | 1080 均值 |
|---|---|---:|---|---:|
| 低分辨率纵向复用，保留奇数几何回落 | +0.0455 / +0.0244 / +0.0097 | +0.0265 | +0.0413 / +0.0235 / +0.0185 | +0.0278 |
| 偶数几何特化，去核内回落分支 | −0.0022 / +0.0115 / +0.0160 | +0.0084 | −0.0070 / +0.0161 / −0.0176 | −0.0028 |
| block69 main → post70 low 改 FP16 | −0.0100 / +0.0096 / +0.0216 | +0.0071 | +0.0005 / +0.0108 / +0.0054 | +0.0056 |

同体异名 control 的单次差值覆盖约 −0.0275～+0.0282ms，特化和 FP16 候选处于这个噪声范围；不能把 1080 特化的 −0.0028ms 当收益。通用复用版各组都慢，加入分支改变了控制流；去掉分支后仍无稳定收益，停止沿此微调。

## 确认实际测到了改动

- host 从当前生产源提取选项，使用 prod8 模块底包；PDL=1，graph/adaptive/dup 关。900=1600×960，1080=1920×1152，输入与 expected 来自现有 network-timeline 固定帧。
- 计时内不做读回，不插逐核事件；每槽计时前后做完整 RGB 逐位比较，全部 bitdiff=0。每帧 post 调用计数为 1，避免假 null。
- ELF 函数体对照：实验模块中的 10 个原核机器码与 prod8 原模块全部逐字节一致；原 post 与同体异名 control 机器码也完全一致。
- 纵向特化：post staging 的静态 b128 从 6 条降到 4 条（包含 2 条 scale 读取），不是仅源码上删了读取。post VGPR 都为 158，LDS 不变。
- FP16 连接：post staging 从 6 条 b128 变成 2 条 b128 + 4 条 b64，skip 的 4 条 b32 保持；post VGPR 158，block69 chain_finish VGPR 153，与原版一致。减少字节的同时增加格式转换，整段/整网未获益；本轮不进一步拆分两者耗时。
- FP16 候选只改 block69 的 main 生产者和 post70 的 low 消费者。block4 的 main/skip 格式不变。block69 原输出已在 FP8 格点上，FP16 精确承载；没有换精度算法，也没有改变加法顺序。分配容量暂未缩小。

本轮是固定输入、无历史的候选筛选，不是全时序回归。候选不采用，因此不追加双架构编译或装机验收。

## 证据与复现

- 工具：`../../HIP/experiments/c32-post-input/` 的 prepare / runner / build / run / analyze / inspect。
- 原始结果：`results-900`、`results-1080`（mode 2）；`results-900even`、`results-1080even`（mode 3）；`results-900half`、`results-1080half`（mode 4）。每目录有 slots.csv 和 run.log，mode 1 是同期 control。
- `binary-check-half.json`：最终模块的原核字节比对、寄存器/指令摘要；`binary-check-even.json`：前一模块原核比对。
- `baseline-hashes.csv` / `source-manifest.json`：底包与源码身份。
- 三次模块 SHA256：通用复用 `5066370a31b121ed310440644e3626c1e10fab15a22ac0401363d7c34099cfb7`；加偶数特化 `3c5f10233e8b2bb15b65a5a445b4fa2b63bd5c965506bd7ca8ee38318525f69e`；加 FP16 连接 `ef9dc7492df6fd1bfd04cf98fd7961336d0af14c48004973acc6b492fbbc2160`。

## 下一方向的旧账校准

已补读 wmma-page-gap / wmma-pitch-gap / wmma-groups-gap 原记录：完整 4MiB 权重上的 padding/xor 没有特殊 span64 那种大收益；旧随机 stride 重排和多 wave 合组还明显变慢。后续不重做特殊 span64、不直接扩大组大小。

若继续 ViT 调度实验，具体候选应是**真实核的一 wave 一组保持不变，只在小范围二维 token tile / 输出列 tile 上重排 group 编号，比较 A 复用与 B 复用的取舍**。这与旧的随机乘 stride 置换、多 wave 合组不同；仍须先证明映射无漏无重，再做真实网络逐位与 ABBA，不能预设 PR #2217 的倍数收益。
