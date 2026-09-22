# C32 栅栏作用域与 CU 模式对照（2026-09-22，Hikari）

起点：[C32 发射周期预算](../../reviews/c32-issue-budget-hikari-20260922.md)第 4a 节。三个 C32 融合基线核里，`sync_window()` / `sync_owned_rows()` 的 workgroup 作用域栅栏在 gfx12 上被编译成 `global_inv scope:SCOPE_SE`（每 wave 18 / 15 / 16 次），每次作废本 CU 的向量 L0。这些栅栏只保护 LDS。

## 变体

同一份融合体，只换同步方式，以 `_pairN` 后缀导出，复用 c32-pair-encode 的隔离 host（按槽把全部 10 个 C32 融合调用切到 `_pair<mode>`）：

| 模式 | 栅栏 | 编译模式 |
|---|---|---|
| 0 | 原版 `fence(…,"workgroup")` | WGP（`.amdhsa_workgroup_processor_mode 1`） |
| 1 | `fence(…,"workgroup","local")`，只覆盖 LDS 地址空间 | WGP |
| 2 | 原版 | CU（`__attribute__((target("cumode")))`，描述符 `workgroup_processor_mode 0`） |
| 3 | local | CU |

barrier 一条不动，矩阵/LDS 布局不动。生成脚本 `Development/HIP/experiments/c32-fence-scope/prepare.py`。

## ISA 变化（gfx1201，isa.json）

| 核 | 静态指令 | global_inv | s_wait_loadcnt_dscnt | s_wait_dscnt | VGPR / Occupancy |
|---|---:|---:|---:|---:|---|
| prefix 原版 / pair1 / pair2 | 3327 / 3310 / 3310 | 18 / 0 / 0 | 22 / 16 / 15 | 103 / 110 / 110 | 153 / 8 不变 |
| chain 原版 / pair1 / pair2 | 3603 / 3589 / 3589 | 15 / 0 / 0 | 25 / 19 / 19 | 57 / 63 / 63 | 177 / 8 不变 |
| post 原版 / pair1 / pair2 | 3013 / 2998 / 2998 | 16 / 0 / 0 | 19 / 14 / 13 | 82 / 88 / 88 | 158 / 6 不变 |

两个效果都来自栅栏：

1. `global_inv` 全部消失（pair1 靠地址空间限定；pair2 靠 CU 模式，编译器在 CU 模式下不为 workgroup acquire 发 L0 失效）。
2. 栅栏前的 `s_wait_loadcnt_dscnt 0x0` 变成 `s_wait_dscnt 0x0`：原版每个栅栏都要等**所有在途全局读取**回来，local 版只等 LDS。这意味着原版栅栏切断了跨阶段的读取预取。

pair1 与 pair2 的函数体只差几条 wait 计数编码（post 18 行 diff，全是标签号和 wait 掩码），pair2 与 pair3 相同。所以 pair2 相对 pair1 的差异几乎全是硬件 CU 模式本身（4 个 wave 落在同一个 CU）的效果，不是代码。

## 整网 ABBA（每槽 160 帧，30 帧预热，24 槽/档，网络原始 FP32 逐位相同，替换数 1600/槽）

| 档 | 测试 | 原版均值 ms | 变体均值 ms | Δ ms | 核心 MHz 中位（A / B） | 显存 |
|---|---|---:|---:|---:|---|---|
| 1080 | pair1 local | 17.834 | 17.671 | −0.163 | 2732 / 2747 | 2505 |
| 1080 | pair2 CU | 17.941 | 17.610 | −0.331 | 2718 / 2732 | 2505 |
| 1080 | pair3 local+CU | 18.007 | 17.661 | −0.346 | 2711 / 2724 | 2505 |
| 900 | pair1 local | 12.783 | 12.670 | −0.113 | 2740 / 2756 | 2505 |
| 900 | pair2 CU | 12.808 | 12.560 | −0.248 | 2734 / 2750 | 2505 |
| 900 | pair3 local+CU | 12.805 | 12.555 | −0.250 | 2732 / 2746 | 2505 |

逐槽数值在 summary.json；每个测试的 4 个变体槽全部低于 4 个原版槽，无交叠。三个测试的原版均值随时间缓慢上升（1080：17.83→17.94→18.01），ABBA 内比较不受影响，但不能跨测试拼差值。变体槽核心频率反而高 12～16MHz，收益不来自频率。

按 C32 段（4.405 / 6.444 ms）算：只去 L0 失效约 −2.5%，加 CU 模式约 −5.4%。相对整网约 −1.9%。

## 对"必要损失"账本的意义

- 这 0.11～0.16 ms 之前一直被记在"C32 就是这么慢"里，实际是编译器为不需要的一致性保险付的账，属于**当前实现的额外工作**，不是算法必要。
- 它同时解释了 kernel-bottleneck 捕获里 post 的 L0 命中只有 71.6%：权重 35 KB 却每个阶段被作废一次。本轮没有重新捕获计数器，命中率变化待测。
- CU 模式额外 0.13～0.17 ms，机制未分离：可能是 4 个 wave 共享同一 L0 提高重用，也可能是 LDS 端口局部化。需要 CU 模式下的计数器捕获才能说。

## 未做

- 未捕获 RGP，L0 命中率的变化只是推断。
- 未改生产源码、游戏 DLL、发布包。若采用，生产改法是在 `hip/c32_fused_ffn_attention.hip` 加开关：栅栏加 `"local"` 第三参数 + 核函数加 `target("cumode")`，重编 selected-modules 后整网回归。
- 其他模块的汇编里同类 `global_inv` 数量：multihead_fused_attention 130、deep_fast 30 / 18（远端 network-fixed-shapes 下 .s 统计，跨多个核）。C64～C512 的 92 次 dispatch 走的正是 multihead 核，这是比 C32 更大的同类账，未测。

## 证据

`900/`、`1080/`：network.csv、run.log、telemetry.log（ADL 只读）。summary.json / isa.json 由 c32-pair-encode/analyze.py 生成。hashes.txt：kernel.hip、gfx1201 汇编、远端 network.exe（与 c32-pair-encode 的 host 同 hash）、两架构 hsaco。远端目录 `D:\DLSSNR-Lab\hip-backend\c32-fence-scope`，本地 `/tmp/c32-fence-scope`。
