# 全网栅栏作用域与 CU 模式（2026-09-22，Hikari）

承接 [c32-fence-scope](../c32-fence-scope-20260922/README.md)：把同样两个改法推到网络里其余三个带工作组栅栏的模块上，看这笔账在全网有多大，以及 CU 模式对大工作组核是不是也有利。

## 集合

| 集合 | c32_fused_ffn | mh_fused | deep_fast | mh_fast |
|---|---|---|---|---|
| 0（生产 selected-modules） | 原版 | 原版 | 原版 | 原版 |
| pair1 | local 栅栏 | local | local | local |
| pair2 | local + CU | local + CU | local + CU | local + CU |
| pair3 | local + CU | local | local | local |

每帧路由 218 次 launch（deep_fast 92、mh_fast 67、mh_fused 49、c32 10），其余模块（mh 的 shift_pack/pool、deep 的 gather 等）不变。

## ISA（gfx1201，isa-markers.txt）

| 模块 | 原版 global_inv | pair1/2 global_inv | s_barrier_signal | 描述符 |
|---|---:|---:|---:|---|
| c32_fused_ffn_attention-packed | ~160（10 核） | 0 | 92 | pair2 全部 workgroup_processor_mode 0 |
| multihead_fused_attention | 130 | 0 | 124 | 同上 22 核 |
| deep_fast-packed | 18 | 0 | 7 | 同上 76 核 |
| multihead-fast-padded-wave-packed | 5 | 0 | 494 | 同上 88 核 |

mh_fast 有 494 处 barrier 但只有 5 处 global_inv：它的同步大多是裸 `s_barrier`，本来就没带栅栏。所以这笔账集中在 c32 和 mh_fused。

## 整网 ABBA（每槽 160 帧，每测试 8 槽，两轮，原始 FP32 逐位相同，路由数 34880/槽）

| 轮 | 档 | 集合 | 原版均值 ms | 变体均值 ms | Δ ms | 核心 MHz（A / B） |
|---|---|---|---:|---:|---:|---|
| 1 | 1080 | pair1 全 local | 17.903 | 17.669 | −0.234 | 2733 / 2752 |
| 1 | 1080 | pair2 全 CU | 18.020 | 18.139 | **+0.118** | 2720 / 2766 |
| 1 | 900 | pair1 | 12.792 | 12.639 | −0.153 | 2745 / 2768 |
| 1 | 900 | pair2 | 12.823 | 12.864 | **+0.041** | 2742 / 2788 |
| 2 | 1080 | pair1 | 17.943 | 17.718 | −0.225 | 2725 / 2745 |
| 2 | 1080 | pair2 | 18.059 | 18.187 | **+0.128** | 2715 / 2760 |
| 2 | 1080 | pair3 混合 | 18.113 | 17.705 | **−0.408** | 2708 / 2727 |
| 2 | 900 | pair1 | 12.835 | 12.685 | −0.150 | 2740 / 2760 |
| 2 | 900 | pair2 | 12.853 | 12.893 | **+0.040** | 2736 / 2782 |
| 2 | 900 | pair3 混合 | 12.858 | 12.577 | **−0.281** | 2734 / 2756 |

显存全程 2505MHz。每个测试的 4 个变体槽与 4 个原版槽都不交叠（summary.json 里 `no_overlap` 全为 true），两轮 pair1/pair2 复现到 0.01ms 内。变体槽核心频率一律比原版高 15～50MHz，pair2 频率最高却最慢，收益和损失都不是频率给的。

## 读法

1. **栅栏改 local 在全网值 −0.23 / −0.15 ms（1080 / 900）**，其中 C32 单独就占 −0.16 / −0.11（上一轮）。mh_fused 的 130 处 global_inv 只贡献约 −0.07 / −0.04：那些核每 wave 的栅栏数少、驻留时间短，L0 失效的代价远小于 C32。
2. **CU 模式不是普适好事。** 全部切到 CU 反而慢 0.12 / 0.04 ms。mh_fast / deep_fast 多数核是 256～512 线程工作组，CU 模式把 8～16 个 wave 挤进一个 CU，抵消了 C32 那边的收益还有余。C32 是 128 线程工作组（4 wave），受益。
3. **混合集合（C32 用 CU，其余只改栅栏）= −0.41 / −0.28 ms，约整网 −2.2%**，等于两部分收益相加，说明两边效应独立。

对"必要损失"账本：全网工作组栅栏的一致性保险费约 0.23 / 0.15 ms，属于实现额外工作，可全部收回；CU 模式是逐核选择题，不是开关。

## 未做

- 未捕获 RGP；L0 命中率变化仍是推断。
- CU 模式只按模块粗切，没有按核逐个试。mh_fused 的 22 核里 128 线程的那部分可能也受益，需要逐核对照。
- 没有检查这些栅栏中是否有个别真的在保护全局内存（改 local 后会变成竞态）。两轮共 40 槽 × 160 帧逐位相同，加上源码里栅栏都紧挨 LDS 读写，但没有形式化审核。生产采用前应逐处过一遍。
- 生产源码、游戏 DLL、发布包未改。生产改法：四个源文件里栅栏加 `"local"`，C32 的 KERNEL 宏加 `target("cumode")`，重编 selected-modules 后整网回归。

## 证据

`run1/`（两集合 host，tests 1～2）、`run2/`（三集合 host，tests 1～3），各含 900 / 1080 的 network.csv、run.log、telemetry.log（ADL 只读）。summary.json 由内联脚本生成（均值、逐槽、频率中位、交叠判定）。hashes.txt：远端全部 hsaco / exe / 生成源 hash 与本地 host hash。isa-markers.txt：八个变体模块的 global_inv / barrier / 描述符模式 / 等待指令计数。远端 `D:\DLSSNR-Lab\hip-backend\fence-scope-all`，本地 `/tmp/fence-scope-all`。
