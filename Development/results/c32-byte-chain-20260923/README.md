# C32 字节链与向量化输入 staging（2026-09-23，Hikari）

起点：核内时间戳（c32-phase-trace）显示输入 staging 是 C32 最大阶段（30.7%），其中"16 条行读到齐"3.5～4.0k 周期/wave（队列），chain/finish 的转换段 3.2～3.5k（f16 读后每值 `F()` + 逐 token 标量选择链）。

## 两步

**字节链（pair1）**：chain 类 launch 以 raw=1 运行，生产者（mapped/chain，HalfOutput）原来写 f16 原值，消费者（chain/chain_finish，RawMapped）读 f16 再做 `F()`。改为生产者按消费者完全相同的表达式 `fp8(F(float((_Float16)v)))` 直接写字节，消费者读 u8 跳过 F。同一缓冲（字节占 f16 分配的前半）。逐位按构造相同。

**向量化 staging（pair2 = pair3，两份复现）**：字节链之上，RawMapped 消费者的 16 条 `global_load_u16/u8` + 16 条 `ds_store_b8` 改为：lane l 负责 token l>>1 的半行 16 字节，行地址由 lane 0..15 的 `mine` 经 `ds_bpermute` 广播，一条 `global_load_b128` + 一条 16 字节 LDS 写（编译成 2 条存储）。窗外 token 置零。

ISA（chain 核 staging 段，至第一个 barrier）：原版 global_load 16（u16）、ds_store 16（b8）、VALU 281；pair1 16（u8）/16/83；pair2 **1（b128）/2/45 + 1 bpermute**。整核 VGPR 151 不变。

## 整网 ABBA（每测试 8 槽 160 帧，逐位同，替换 1600/槽）

| 轮 | 档 | pair1 字节链 | pair2 +向量化 | pair3（复现） |
|---|---|---:|---:|---:|
| r1（三份都是字节链） | 1080 | −0.027 / −0.027 / −0.046 | | |
| r1 | 900 | −0.019 / −0.020 / −0.015 | | |
| r2（prepare 断言失败，实为字节链再测三份） | 1080 | −0.030 / −0.020 / −0.037 | | |
| r2 | 900 | −0.031 / −0.004 / −0.019 | | |
| r3 | 1080 | −0.034 | **−0.076** | **−0.083** |
| r3 | 900 | −0.025 | **−0.058** | **−0.064** |

字节链单独 −0.02～0.03 ms、多数与噪声交叠；加向量化后 −0.08/−0.06 ms，槽间分开。

## 读法

- **读取字节减半 + 去掉 F() 几乎没用；把 16 条读请求并成 1 条才有用。** 排队等待按请求数计，不按字节数——与 ViT 段"L0 请求数是变量"同一结论，这次在 C32 消费端独立验证。
- 只覆盖 4 个 RawMapped launch（chain×2、finish×2，约 C32 wave-周期的 40%）。mapped/post 读 f32 行（128B），同样可并成 4 条 b128 + 转换后 dword 写；prefix 有自己的 staging。这是下一刀。
- 生产者侧 `out` 仍是 16 条 `global_store_b8`/lane（列主布局），要并成 b64 需投影 WMMA 转置，但残差 `saved_ffn` 在原布局，跨 lane 搬运不免费，未做。

## 采用

`HIP_C32_BYTE_CHAIN`（默认 1）进生产源码，含生产者字节写、消费者字节读、向量化 staging。**约束**：raw 缓冲变为字节，`boundary_fast c32_finish_crop_half`（SkipChainFinish，C32 跳块路径）仍按 f16 读，不能与本开关同用；生产 skip 42/43/46 不涉及 C32 块。正式回归见 deployments/stellar-prod3-20260923。

证据：r2/、r3/（900、1080 各 network.csv、run.log、telemetry.log）、r1～r3 控制台日志。r1 的远端目录在移动时丢失 run.log，数值以控制台日志为准。工具 HIP/experiments/c32-byte-chain。
