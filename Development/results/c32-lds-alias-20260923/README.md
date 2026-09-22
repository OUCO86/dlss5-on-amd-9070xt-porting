# C32 in16 别名到 Scratch：三核 LDS 19712→15360，驻留 6→8 wave/SIMD（2026-09-23，Hikari）

起点：[launch 级驻留账](../launch-occupancy-20260923/README.md)——C32 十核里 mapped ×2 和 post_merge_head（合计 2.17ms/1080，占 C32 39%）的 LDS 是 19712 B/组，CU 模式 64KB 只放 3 组，HW_ID 数出 6 wave/SIMD；其余七核 15360 B 放 4 组、8 wave/SIMD。多出的 4352 B 是 `in16`：Mapped 且非 RawMapped 的核把 staging 后的 f16 行留一份给 mode-0 残差初始化用。

改法：`in16` 不再单独分配，指到 `scratch.ex`。生命期不交叠：in16 写于 staging、最后一次读在 FFN 之前的残差初始化；Scratch 第一次写在 QKV 归一化（`scratch.raw`），中间隔着 FFN 前后两个 `sync_window`；`scratch.hidden` 在 FOLDED_FFN 下不编译。每个区间内的值和地址模式不变，逐位按构造相同。

ISA（gfx1200.hsaco.s）：十个 `_pair` 核 `group_segment_fixed_size` 全部 15360，VGPR 与原版逐核相同（mapped 169、post_head 158、post_fused 153）。

## 整网 ABBA（每测试 8 槽 160 帧，逐位同，三份复现）

| 档 | rep1 | rep2 | rep3 | 槽不交叠 |
|---|---:|---:|---:|---|
| 1080 | −0.091 | −0.091 | −0.094 ms（−0.54%） | rep2/3 是，rep1 差 0.01 |
| 900 | −0.058 | −0.061 | −0.060 ms（−0.49%） | 三份都是 |

核心频率中位 2737 / 2756 MHz（ADL 只读）。基线 = prod5 候选（含字节链、mh 寄存器化）。

读法：三个核 1080 合计约 2.17ms，−0.09 是 4%；驻留 +33% 只换来 4%，说明这三核在 6 wave/SIMD 时延迟已盖住大半（阶段账 barrier 8.7%、矩阵 5%，其余是取数与 LDS 中转，本来就有一半以上的发射槽在用）。收益小但干净，进生产源（`HIP_C32_IN16_ALIAS`），攒进下一批候选。

## 证据

`1080/`、`900/`：run.log（UTF-16）、network.csv、telemetry.log；console.log。工具 HIP/experiments/c32-lds-alias（host 复用 c32-byte-chain 的 kernel 后缀 ABBA host，sha256 4944855C…）；远端 D:\DLSSNR-Lab\hip-backend\c32-lds-alias。
