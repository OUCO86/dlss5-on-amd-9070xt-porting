# 单 wave C32 阶段账与输入宽读（2026-09-26）

基线：当前生产 prod8 + wave-owned + PDL=1 + C512_M32 + VIT_PROJ_N64（0.31）。C32 十块全是 `hip/wave_owned_c32.inc` 的单 wave 核（prefix0、mapped1/66、chain2/3/67/68、finish_dcrop4、finish69、post70）。旧的 `c32-phase-current-20260925` 量的是 4-wave 核，已经过时。

## 方法

`Development/HIP/experiments/c32-wave-phase`：prepare.py 把 `cw_body` 复制成 `cw_phase_body<Phase>`，在代码段边界读本地 20 位 SHADER_CYCLES（`s_getreg_b32 hwreg(29,0,20)`）。段落在 qt 循环里的，四个 tile 的周期累加。每个阶段单独编成一个核变体（6 个入口 × 11 个阶段）；生产核留在同一个模块里，机器码与生产 c32-wave1 逐条相同（16 个函数）。每 32 个窗口抽 1 个，由 lane0 写 {阶段周期, 整核周期, 窗口号, magic}；8 帧轮换抽样余数。每个阶段按"正常/插桩/插桩/正常"四槽 × 80 帧计时，逐位核对输出（两档共 177 次 VERIFY 都是 bitdiff=0）。

份额 = Σ窗口数 × 该段周期均值 / Σ窗口数 × 整核周期均值（同一次插桩运行内）。这是发出的 wave 周期占比，不是墙钟份额。

**局限**：计时指令带 `memory` 屏障，只拦得住访存，拦不住纯寄存器运算。第二个 qt 循环（scores/exp → 求和/概率 → AV → 投影/写出）的算术被编译器挪到了投影段，前三段读数几乎为 0，所以这四段只能合起来看。"特征打包"和"QKV"之间的边界同理，合并看更可靠。插桩扰动（插桩槽减正常槽）大多在 ±0.03ms，QKV 段在 +0.10～+0.15ms；读数只用来排序，不当精确账。

## 阶段账（两档几乎一样）

| 段 | 900 | 1080 | 性质 |
|---|---:|---:|---|
| 输入读取/转换（prefix 含噪声生成与 prefix 投影） | 24.5% | 24.5% | **访存**：mapped/post 每 lane 每个 tile 几十条逐元素 b32/u8 读 |
| FFN 展开/激活/收缩 | 37.6% | 37.7% | 矩阵 + 激活多项式/FP8 打包的 VALU 链 |
| 特征打包 + QKV/归一化 | 11.7% | 11.5% | 矩阵 + 平方和/rsq |
| 注意力 + 投影 + 写出（loop 2 合计） | 10.3% | 10.2% | 分数的 exp 映射与 FP8 打包是 VALU 串行链（与 ViT attention 同类） |
| 尾部（finish 下采样 / prefix main8 / post RGB） | 9.8% | 9.8% | LDS 读 + 全局写 |

按核（占该核整核周期）：post 输入段 **49%**、mapped 输入段 35%、prefix 输入段 20% + 尾部 21%、chain FFN 57%、finish 尾部 23～26%（完整见 `ledger-*.csv`）。post 窗口数最多（24k/35k），它的输入段单独就占 C32 总 wave 周期约 14%。

## 候选（逐位不变）

post 核的 ISA：每 lane 每个 tile 发 69 条 `global_load_b32` + 16 条 `global_load_u8`。低分辨率特征、FP8 skip、`scales[c]`、`scales[32+c]`、`fw[8704+c]` 各 8 个连续通道，逐元素去读。编译器没合成宽读，是因为读取包在 `if(valid)` 里、指针只知道 4 字节对齐。mapped 也是同样情况（34 条 b32）。

`CW_VEC_INPUT=1`（hip/wave_owned_c32.inc）：8 个连续通道用 `__builtin_assume_aligned` + memcpy 整行读取（f32 为 2×b128，skip 字节为 1×b64；基址来自 hipMalloc，通道偏移是 8 的倍数，32 字节对齐），逐元素算术和顺序不变。post 读指令变为 5×b32 + 51×b128 + 23×b64，mapped 变为 2×b32；VGPR 176/165 不变、零溢出。

实验 `Development/HIP/experiments/c32-vec-input`：整模块替换 c32-wave1，两档各 3 组 200 帧 ABBA，每槽首尾 RGB 逐位；外加 16 帧动态历史 × 3 候选，全部 bitdiff=0（`cand-*/`）。

| 候选 | 900 | 1080 |
|---|---:|---:|
| 1 宽读 | −0.092ms（−0.86%） | −0.124ms（−0.82%） |
| **2 宽读 + CW_PREFIX_SPLIT** | **−0.114ms（−1.06%）** | **−0.142ms（−0.94%）** |
| 3 仅 CW_PREFIX_SPLIT | −0.018 | −0.031 |

三组差值方向一致。候选 2 采用。

## 生产接入

- 配方：`hip/build-modules.ps1` 的 c32-wave1 与 `Development/HIP/prepare_wave_owned.py` 都加 `CW_VEC_INPUT 1`、`CW_PREFIX_SPLIT 1`。不新增开关，跟 `DLSS5_HIP_WAVE_OWNED=1` 走；add-on 与 host 不变。
- 双架构编译（`Development/deployments/c32-vec-20260926/build.ps1`）：gfx1201 `7AC34418…`、gfx1200 `128BB82C…`（gfx1200 只编译，没有实机）。gfx1201 生产模块的 16 个函数，与实测的 cvi-vecsplit 逐条相同（去掉 `__hip_cuid` 后）。
- NativeGameFrame 回归（同一生产 host 与 flags，A = vit-proj-n64 生产模块集，B = 换 c32-wave1）：900/1080 静态与运动、720 运动、900/1080 连续历史，7 个用例 84 帧逐帧哈希相同。
- 生产 host 千帧长测（去前 200 帧，槽 0/3 基线、1/2 候选）：900 10.935→10.846ms（**−0.088，−0.81%**），1080 15.269→15.129ms（**−0.140，−0.92%**）；每个槽最终输出哈希相同。
- payload：AMD 机 `D:\DLSSNR-Lab\c32-vec-20260926\payload\{gfx1200,gfx1201}\c32-wave1.hsaco` + `install.ps1`（先核对旧哈希 E2EDB93A/73A2DFDB，再备份、替换、回读；可用 `-RestoreBackup` 回滚）。**没有安装，没有发包。**

## 下一步

FFN（37.7%）是最大段，但它是矩阵 + 激活/FP8 打包 VALU 链，形状跟 ViT attention 那条"exp 映射 + FP8 打包"类似，逐位约束下不宜硬砍。更值得做的是 finish/prefix 的尾部（占各自核的 21～26%）：main8/down 写出和 LDS 读的组织方式。
