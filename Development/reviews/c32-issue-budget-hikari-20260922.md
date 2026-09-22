# C32 发射周期预算：把静态指令折成每 wave 的管线周期（Hikari，2026-09-22 20:50）

目的：回应交接说明第 5 点。静态指令比例不能当时间比例，所以这里不做饼图，而是按管线分别算"每 wave 至少要占多少发射周期"，再乘 wave 数和 4.4ms 对账，得到**下界**。凡是假设的硬件常数都单独列出，可以被替换。

数据来源：`/tmp/c32-pair-encode/kernel.s` 三个无 `_pairN` 后缀的基线导出；wave 数来自 `results/network-timeline-20260921/900/timeline.csv` 的 group 数（该 csv 的耗时是密集标记版，只取几何，不取时间）。

## 1. 静态指令按管线分类（每 wave 一次执行）

三个核各只有一个真正的内层循环（`Inner Loop Header: Depth=1`，FFN 展开 `for col<128 step 16`，2 条 WMMA/次，首次剥离、循环体再跑 7 次）。其余 `#pragma unroll` 全部展平。

| 核 | 循环外 VALU | 循环外转换 | 超越函数 | WMMA fp8 / f16 | LDS 指令 | VMEM | s_wait | barrier | global_inv | 循环体（×7） |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| prefix_finish_main8 | 1264 | 526 | 33 | 60 / 12 | 429 | 106 | 327 | 11 | 18 | VALU 68、WMMA 2、LDS 8、VMEM 2 |
| chain | 1447 | 400 | 26 | 60 / 8 | 379 | 128 | 452 | 9 | 15 | VALU 64、WMMA 2、LDS 8、VMEM 2 |
| post_merge_head | 1321 | 422 | 26 | 48 / 8 | 409 | 108 | 264 | 9 | 16 | VALU 61、WMMA 2、LDS 8、VMEM 2 |

分类脚本：scratchpad `classify.py`（前缀匹配 v_wmma / v_cvt / 超越函数 / v_ / ds_ / global_load|store / global_inv / s_wait / s_barrier）。VOPD 双发射指令按 1 条计。

动态每 wave（循环外 + 7×循环体），post 为例：VALU 约 2170，WMMA fp8 62 + f16 8，LDS 465，VMEM 122。**非矩阵 VALU 与 WMMA 条数比约 31:1。**

## 2. 每条指令的周期假设

| 项 | 取值 | 依据 |
|---|---|---|
| WMMA fp8 16×16×16 | 16 周期/SIMD | 由本机实测 405 TF、3.14 GHz、64 CU×4 SIMD 反推：405e12 ÷ (3.14e9 × 256) ≈ 504 FLOP/周期/SIMD，8192 ÷ 504 ≈ 16 |
| WMMA f16 16×16×16 | 32 周期/SIMD | 同法，204 TF 反推 |
| 普通 VALU（wave32） | 1 周期 | RDNA 通用假设，未单独实测 |
| 超越函数（rcp/rsq/sqrt/log/sin/cos） | 4 周期 | RDNA 四分之一速率，未单独实测 |
| LDS | 128 B/周期/CU | RDNA3 公开值，RDNA4 未核实。ds_load_2addr_b32 wave32 = 256 B → 2 周期；ds_store_b8 = 32 B 但仍占 1 条发射 |
| VMEM | 64 B/周期/CU | RDNA3 启发式，RDNA4 未核实。b64 → 4 周期，b32 → 2，u8 → 1 |

WMMA 和 VALU 是否共用同一发射口，我没有 RDNA4 的确定资料，所以下面给两个界。

## 3. post_merge_head 对账（900P）

wave 数：24321 组 × 4 wave = 97284；每 SIMD 约 380 wave，每 CU 约 1520 wave。

| 管线 | 每 wave 周期 | 每 SIMD/CU 累计 | 折时间（3.1 GHz） |
|---|---:|---:|---:|
| WMMA | 62×16 + 8×32 = 1248 | 380 × 1248 = 474k | 0.15 ms |
| VALU（含超越函数补差） | ≈ 2270 | 380 × 2270 = 863k | 0.28 ms |
| LDS（按 CU） | ≈ 520 | 1520 × 520 = 790k | 0.26 ms |
| VMEM（按 CU） | ≈ 370 | 1520 × 370 = 562k | 0.18 ms |

密集标记版 post 约 1.10 ms，干净重建的 C32 全段 4.405 ms 里 post 大致 1.0 ms 量级（未单独干净测，取范围 0.9～1.1）。

读法：

- **矩阵管线只需 0.15 ms，占 post 耗时约 15%。** 这个数只依赖 WMMA 周期反推和 wave 数，是最硬的一条。也就是说 post 里 85% 左右的时间，不管归到谁头上，都不是矩阵单元在干活。
- **VALU 发射 0.28 ms**：转换/激活/softmax/归一化的算法工作。这一格大部分是"必要功能"，但当前实现里 422 条转换指令的必要性没证明（pair-encode 只证明了配对转换不省时间，没证明转换总量不能减）。
- **四条管线串行相加 ≈ 0.87 ms，接近实测。** 理想情况下四条管线应该重叠，实测接近串行和，说明重叠很差：wave 在 s_wait 上等。264 条 s_wait、9 次 barrier 每 wave，占用 6 wave/SIMD 的驻留，难以互相掩盖延迟。这和 kernel-bottleneck 捕获的 memory unit busy 99%、stalled 5.5% 相符：内存单元一直有活但不是排队，是被零碎请求占满。

上界/下界：若 WMMA 与 VALU 共用发射口，矩阵利用率上限 = 1248 ÷ (1248+2270) ≈ 35%；若完全独立，上限 = 1248 ÷ 2270 ≈ 55%。**两种假设下 VALU 发射都先于矩阵成为瓶颈**，这一点不依赖发射口模型。

## 4. 两个具体、便宜、之前没测过的对照

### 4a. 每 wave 16 次 global_inv（L0 失效）

`sync_window()` 用 `__builtin_amdgcn_fence(3,"workgroup")` + `s_barrier` + `fence(2,"workgroup")`。gfx12 上 workgroup 作用域的 acquire 栅栏被编译成 `global_inv scope:SCOPE_SE`（post.s 第 842、954、1117、1279、1335、1477、1519 行等，共 16 处），每次把本 CU 的向量 L0 整个作废。post 的权重只有约 35 KB，本该几乎全在 L0 命中，捕获却只有 71.6%。这些栅栏保护的是 LDS 数据，不是全局内存，L0 失效是编译器为"workgroup 可能跨 WGP 两个 CU"付的保险。

对照设计（输出应逐位不变）：

1. 编译加 `-mcumode`：工作组限定在单 CU，LLVM 内存模型在 CU 模式下不为 workgroup acquire 发 L0 失效。数 `global_inv` 是否归零，看 L0 命中率和整网时间。
2. 或改栅栏为只覆盖 LDS 地址空间：`__builtin_amdgcn_fence(3,"workgroup","local")`（新版 clang 支持第三个参数），同样应去掉 global_inv。
3. 控制：保留 barrier 不动，只改栅栏。这与"盲删 barrier 破坏逐位"是不同实验。

三个核都受影响（18 / 15 / 16 处），11 次 dispatch 全在内。

### 4b. LDS 字节粒度写入

post 每 wave 136 条 `ds_store_b8` + 64 条 `ds_store_b16` + 64 条 `ds_load_u8`，同样字节量若先在寄存器打包成 b32 再写，LDS 指令数可降到约四分之一。pair-encode 三个变体的 `ds_store_b8` 仍是 136 条（已核对 `_pair3`），所以"转换配对"和"写入宽度"是两件事，后者没测过。这一项改动会动指令调度，收益不保证，但 LDS 管线 0.26 ms 是它的上限。

## 5. 这一页不声称什么

- 没有 RDNA4 的 L0/LDS/VMEM 精确服务率，表 2 的 LDS/VMEM 行是启发式，只用来看数量级。
- 没有动态执行计数，循环 7 次是从汇编计数器读的（`s_cmp_lt_u32 s2, 0x70`），分支剥离部分按执行一次计。
- 0.15 ms 的矩阵下界不等于"可回收 0.85 ms"。VALU 那格里大部分是算法必需的工作。
- 对账用的 post 干净耗时是估的（0.9～1.1 ms），要真对账得单独测一次 post。
