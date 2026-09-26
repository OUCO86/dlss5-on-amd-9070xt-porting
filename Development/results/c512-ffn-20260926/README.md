# C512 FFN 链：32 token/wave 的 QKV 与 mix（逐位，900 −1.0%，1080 −1.3%）

2026-09-26，朱雀分身。对照 = 当前生产（prod8 + wave-owned 46 块 + PDL=1）。起因：逐族账里 C512 是唯一没动的族（1080 2.23ms），注意力一头一 wave 已是 null（`../c512-wave-20260926`）。

## 1. 分账：重复派发边际成本（13 块/帧合计，2 轮 ABBA）

| 核 | 900 ms | 1080 ms |
|---|---:|---:|
| split_mix_blocked_h16w | 0.277 | 0.416 |
| split_ffn_fused_fp8_t8 | 0.231 | 0.289 |
| split_projection_frag | 0.162 | 0.236 |
| **mh_qkv_normalize_frag_c512** | **0.603** | **0.504** |

四个核都是「一个 wave = 16 token × 64 列」，每 16 token 就把自己那 64 列权重全读一遍：QKV 1080 档单次约 424MB 的 L2 权重流量（13 块 5.5GB/帧）。QKV 另有 32 条 `global_store_b8`/lane 的字节尾巴。

## 2. 候选（`HIP/experiments/c512-ffn`，模式号见 `experiment-manifest.json`）

900/1080 各三组 200 帧 ABBA，每槽首尾 RGB 逐位 + 16 帧动态历史，全部 bitdiff=0。

| 模式 | 改动 | 900 | 1080 | 结论 |
|---|---|---:|---:|---|
| 5 | QKV 字节尾巴经 LDS 拼 16×64 后每 lane 2 条 b128（32 b8→2 b128） | −0.04ms | −0.04 | 小 |
| 6 | QKV 一 wave 32 token（两 A 片段共用 B） | −0.07～−0.10 | −0.09～−0.10 | **采用** |
| 7/8 | QKV 48/64 token | +0.04/+0.05 | −0.02/+0.03 | 溢出（scratch 40/48B），否 |
| 9 | split_projection_frag 32 token | +0.01 | +0.02 | null，否 |
| 10 | split_mix_h16w 32 token | −0.03～−0.04 | −0.12 | **采用** |
| **12** | **6 + 10** | **−0.122（−1.12%）** | **−0.216（−1.40%）** | **进生产** |

判断：C512 FFN 链的限制是**供数（每字节权重只喂 16 token）**，不是写出条数；把 M 从 16 翻到 32 兑现最多，64 时寄存器溢出反亏。投影核同形状却不赚——其 A 读 + 残差初值读占比更大，未深究。

## 3. 生产可选路径

- 源：`hip/c512_m32_mh.inc`（`mh_qkv_normalize_frag_c512_m32`）、`hip/c512_m32_deep.inc`（`split_mix_blocked_h16w_m32`），配方新增两个独立模块 `c512-m32-mh` / `c512-m32-deep`（28 模块），原 24+2 模块源码不变。
- 开关 `DLSS5_HIP_C512_M32=0/1`（默认 0），`C512M32Compatible`：仅在生产 h16w-mix + split FFN fused + proj tiles + QKV frag 配置下激活，其他布局保持原路径；激活时模块缺失 = 加载错误（与 wave-owned 同策略）。`native-hip.txt` 记 `c512_m32_requested/active`。
- 机器码：生产配方编出的两个核与实验测过的逐条相同（去地址后 ISA diff 为空）；双架构编译，gfx1200 仅编译。模块 hash 见 `production-build-manifest.json`。
- **完整 NativeGameFrame 回归**（`deployments/c512-m32-20260926/regression.ps1`，两侧均 WAVE_OWNED=1 PDL=1）：900/1080 × 静态/移动 12 帧、720 移动、900/1080 连续历史，候选与基线逐帧 SHA 相同；trace 计数每帧 26 次（13 块 × mix+QKV）全部替换；关 `SPLIT_MIX_H16W` 回落用例 replaced=0。
- **生产 host 长测**（每槽 1000 帧去前 200，ABBA）：900 11.114→11.005ms（**−0.110，−0.99%**），1080 15.683→15.481ms（**−0.203，−1.29%**）。
- payload（未入库二进制，AMD 机 `D:\DLSSNR-Lab\c512-m32-20260926`）：add-on `3d8295db…`（含 cd0fea6 auto-tier）+ 4 模块；`install.ps1` 预检 wave-owned 已开、已知 add-on hash、备份/失败回滚/`-RestoreBackup`。**未安装、未发包。**

## 4. 发现的既有风险：生产路径历史模式偶发不一致

回归中一次 **基线**（C512_M32=0，即现行生产）900 连续历史用例第 8～11 帧与其余 20+ 次同条件运行不同（候选同次正确）；随后基线/候选各 6 次复跑全部逐位相同。与本改动无关，疑为 PDL 可见性/复用（WorkingPlan「PDL：先补正确性依据」一直未结案）。建议单独做高次数（≥50）PDL=1/0 历史重复对照定位。

## 限制

固定输入 + NativeGameFrame 回放，不是游戏帧率；gfx1200 无实机；投影 m32 null 的原因未拆。
