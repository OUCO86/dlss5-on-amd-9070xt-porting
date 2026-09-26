# ViT attention 与 C32 输入准备：五个逐位候选（2026-09-26）

对照基线 = 当前生产：prod8 + wave-owned + PDL（测量时 PDL=0，同 m32-sweep）+ C512_M32 + VIT_PROJ_N64，模块取 `hip-backend\vit-proj-n64-production\modules-gfx1201`。工具 `Development/HIP/experiments/vit-attn-c32-input/`（m32-sweep 派生：`prepare.py` → /tmp/vac，候选核在 `cand_deep.inc` / `cand_c32_prefix.inc`，替换规则 `cand_remap.inc`）。每候选 900/1080 各三组 200 帧 ABBA，槽首尾最终 RGB 对 capture 的原始 FP32 逐位 + 16 帧动态历史（位移/增益/黑白、非零种子、带 history）逐位。**五个候选全部 bitdiff=0。**

## A. ViT attention（`vit_attention_fused_{400,640}_bytein`，一 wave = 16 query × 1 head 扫全部 key）

| 候选 | 改动 | 900 | 1080 |
|---|---|---:|---:|
| A1 m32 | 一 wave 两个 query tile 共用 K/V 读取（wave 数减半） | +0.077 ms | +0.082 ms |
| A2 vt | QKV 生产者把 V 转置写成 [通道][token]（8 字节合并写），注意力 V 片段一次 8 字节读 | −0.010 | −0.012 |
| A3 swap | QK MMA 对调操作数直接得 S^T，去掉每块 LDS 转置 + 两道 fence + s_barrier | −0.031 | +0.016 |
| A4 = A2+A3 | | −0.020 | −0.002 |

结论：**不卡访存量（A1 更慢：并行度减半的损失大于少读）、不卡 V 字节 gather（A2 零）、不卡每块的 LDS/barrier 依赖链（A3/A4 零）。** 静态 ISA 以逐元素 VALU 依赖为主（exp 位映射：乘、med3、移位、fp8 打包；87 条 `s_delay_alu`），瓶颈在每元素标量运算链的延迟，逐位约束下已无结构性空间。四个候选均不采用。

## B. C32 输入准备：prefix 特征两半 wave 分摊（B1）

`c32_wave1_prefix` 原来只有 g==0 的 16 lane 算每 token 16 个输入特征（Box–Muller 三个噪声：PCG、4 个均匀数、2 log、2 sqrt、2 cos、1 sin + RGB/历史），另 16 lane 空等，再用 8 次 bpermute 搬后 8 项。B1 让两半 wave 执行同一指令流：g==1 选 (a,c) 算 g0、g==0 选 (b,d) 算 g1/g2，g0 一次 bpermute 交换；每个值的运算序列与 `fused_prefix_values` 相同。

| | 第一轮（3×200） | 加长（6×300） |
|---|---:|---:|
| 900 | −0.0135 ms | −0.0078 ms |
| 1080 | −0.0241 ms | **−0.0341 ms（6 组全负）** |

1080 小而稳定（约 −0.2%），900 在噪声内。已以宏 `CW_PREFIX_SPLIT`（默认 0）并入 `hip/wave_owned_c32.inc`；默认编译路径不变，未改配方、未进生产、无部署包——收益不值单独一次模块发布，待下轮合包重编 c32-wave1 时打开并做完整 NativeGameFrame 回归。

## 限制

- 固定输入回放 + 动态历史 16 帧，不是游戏内实测；PDL=0 测量（同 m32-sweep 口径）。
- C32 其余输入准备（chain 的 `cw_input` 坐标/边界、mapped 的 half 转换）未改；旧 c32-phase-current 账是 prod8 4-wave 核，单 wave c32-wave1 的阶段比例需重测后再选刀。
- 原始数据：`slots-<高>-<a1..a4|b1|b1long>.csv`；b1 模块构建清单 `build-manifest-b1.json`。
