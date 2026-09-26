# m32-sweep：把"一个 wave 算更多 token / 列"推广到其余核（2026-09-26，朱雀分身）

起因：c512-ffn 把 C512 的 QKV 与 mix 从 16 token/wave 改 32，读权重减半，−1.3%。本轮普查其余现役核，挑前几名做同类候选。
对照 = 当前生产（prod8 + wave-owned 46 块 + C512_M32=1；普查 PDL=0，因为重复派发 `_pdl` 核会重复计数旗子；候选 PDL=0）。
工具 `Development/HIP/experiments/m32-sweep/`（`prepare.py` 生成带 `SetDup()`/`SetCand()` 的生产 host 副本，`runner.cpp.in` 一进程内 ABBA，`abba.py` 算配对差）。原始槽数据 `csv/`，汇总 `abba-summary.txt`，核资源 `kernel-resources.txt`。

## 1. 普查：重复派发边际成本（每帧合计，2 轮 150 帧 ABBA）

| 核（当前默认派发） | 次/帧 | 900 ms | 1080 ms |
|---|---:|---:|---:|
| C256 生产 FFN+QKV `mh_ffn_fused_c256_frag_project*_bytein_fb` | 16 | **0.925** | **1.322** |
| `vit_attention_fused_*` | 8 | 0.358 | 0.555 |
| `vit_qkv_project_normalize_fused_f16compact_fp8_frag` | 8 | 0.340 | 0.541 |
| `decoder_project2x_h16w{,_byteout}` | 5 | 0.340 | 0.460 |
| `vit_project_frag` | 8 | 0.236 | 0.408 |
| `vit_expand_blocked_fp8_frag_bytein` | 8 | 0.221 | 0.303 |
| `split_ffn_fused_fp8_t8` | 13 | 0.239 | 0.285 |
| `vit_contract_blocked_fp8_frag` | 8 | 0.187 | 0.283 |
| `mh_pool_project*` | 5 | 0.148 | 0.262 |
| `split_projection_frag` | 13 | 0.183 | 0.207 |
| `mh_shift_pack` | 13 | 0.116 | 0.143 |
| `vit_pack_input` | 8 | 0.011 | 0.019 |

重复派发的输出全部与原输出相同（这些核都是纯函数）。

**排序不能只看成本，要看离峰值多远。** C256 FFN 每 token ≈1.11 MFLOP（expand 0.52 + QKV 0.39 + project 0.13 + 分组 contract 0.07），1080 一次 34560 token = 38 GFLOP；边际 82 μs/次 ≈ 460 TFLOPS，已在 FP8 WMMA 405T 峰值附近（边际法对连发会略低估）——**算力瓶颈，不是供数瓶颈**。ViT QKV ≈60 TF（FP16，峰值 204T 的 30%）、ViT project ≈26 TF，离峰值远。

## 2. 候选（900/1080 各三组 200 帧 ABBA，每槽首尾 RGB 逐位 + 16 帧动态历史，全部 bitdiff=0）

| # | 改动 | 资源 | 900 | 1080 | 结论 |
|---|---|---|---:|---:|---|
| 1a | C256 FFN 32 token/组（按源码默认 LINE_STORES=0 写） | 118 VGPR, LDS 43 KB | — | +0.163 | 否 |
| 1b | 同上，照生产 prod8 的 LINE_STORES=1 整行写尾部 | 181 VGPR, LDS 60 KB | — | +0.036 | 否：算力瓶颈，读权重减半无用，LDS/寄存器翻倍反拖驻留 |
| 2 | ViT QKV 32 token × 64 列 | 136 VGPR | +0.170 | +0.136 | 否：wave 数 3840→960（900: 624），延迟藏不住 |
| 3 | ViT QKV 32 × 32 | 79 | +0.098 | +0.179 | 否 |
| 4 | ViT QKV 16 × 64 | 82 | +0.068 | −0.051 | 否（两档不一致） |
| 5 | ViT project 16 × 32 | 90 | −0.043 | −0.229 | 可，但不如 6 |
| **6** | **ViT project 16 × 64** | **160** | **−0.105 / −0.112 / −0.101** | **−0.300 / −0.289 / −0.281** | **采用**（三批复现） |
| 7 | ViT project 32 × 32 | 99 | −0.016 | −0.167 | 否 |
| 8 | decoder 投影 16 × 64（输出 32 列档用 32） | 128 | +0.114 | +0.139 | 否：2×2 上采样尾部每元素散写 4 处，加宽后串行尾部×4、wave 数÷4 |
| 10 | 6 + 8 | — | +0.009 | −0.155 | 否 |

ViT project 的限制在 A 端：每个 K16 步要把 8 个 f32 输入现转 E4M3，生产一次只喂 1 个 WMMA；16×64 让同一 A 喂 4 个。32 token 方向（两 A）反而不如只加宽 N。

**编译形态影响很大**：同算术的手写特化版（98 VGPR，772 条指令）同批只有 −0.044/−0.225（候选 11 对 6 的 −0.101/−0.281）。生产 `hip/vit_wide_deep.inc` 因此直接用实测的模板原文（只实例化 TM=1,TN=4），生产模块里该核去地址后 ISA 与实测核逐条相同（1637 条，0 行差异）。

## 3. 生产可选路径

- 源 `hip/vit_wide_deep.inc`（`vit_project_frag_n64`），配方新增模块 `vit-wide-deep`（29 模块），原模块源码不变。
- 开关 `DLSS5_HIP_VIT_PROJ_N64=0/1`（默认 0），`VitProjN64Compatible`：`vit_proj_frag && fast_deep && packed_weights` 才激活；`native-hip.txt` 记 `vit_proj_n64_requested/active`。
- 模块：gfx1201 `AD8642DA…`，gfx1200 `20AD91A8…`（gfx1200 仅编译）。add-on `106ff3d0…`（含 auto-tier 与 C512_M32 解析）。
- **完整 NativeGameFrame 回归**（`deployments/vit-proj-n64-20260926/regression.ps1`，两侧 WAVE_OWNED=1 PDL=1 C512_M32=1）：900/1080 × 静态/移动 12 帧逐帧 SHA 相同；720 移动、900/1080 连续历史相同；关 `VIT_PROJ_FRAG` 回落用例相同且替换 0；计数每帧 8 次全部替换。
- 生产 host 千帧长测：**未跑**——跑到这一步时 Zero 开了《剑星》，按规矩停手。性能依据目前是上表的网络 ABBA（三批一致）。
- payload（未入库二进制）`D:\DLSSNR-Lab\vit-proj-n64-20260926`：add-on + 2 模块 + `install.ps1`（预检 WAVE_OWNED/C512_M32 已开、已知 add-on 3d8295db、备份/失败回滚/`-RestoreBackup`）。**未安装、未发包。**

## 4. 顺带发现：配方缺 `HIP_FFN_LINE_STORES 1`

prod7/prod8 的 mh_fast 模块都是带 `HIP_FFN_LINE_STORES 1` 编的（`deployments/stellar-prod7-20260924/build.ps1`、AMD 机 `prod8/mhfast.generated.hip`），但 `hip/build-modules.ps1` 的 mh_fast 行只有 `HIP_FFN_HOIST_RES 2`，源码默认 0——按配方重编会悄悄丢掉 prod7 的整行写（逐位不变，但慢 0.6/0.7%）。已补上该行；补后配方拼出的源码与 prod8 的 `mhfast.generated.hip` 逐字节相同。

## 限制

固定输入网络 ABBA + NativeGameFrame 回归，不是游戏帧率；生产 host 长测待补；gfx1200 无实机。ViT attention（边际第二）未做：K/V 每头 40 KB 在 L0 内，加宽 query 的收益存疑，留作下一轮。
