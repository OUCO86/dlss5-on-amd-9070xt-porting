# C512 一头一 wave（attention/projection-only）——逐位通过，无收益，不采用

2026-09-26，朱雀分身。对照 = 当前生产（prod8 + wave-owned 46 块 + PDL=1，模块 `wave-owned-production\modules-gfx1201`），固定 HDR 捕获输入（network-timeline 900/1080），每档 3 组 ABBA × 200 帧（20 帧预热），每槽首尾 RGB 与捕获期望逐位比较，另 16 帧动态历史（位移/增益/黑白/seed=123+17f，首帧无历史）对当场 baseline 逐帧比较。

## 做了什么

`c512_attn_wave`（`Development/HIP/experiments/c512-wave`）：一个 8×8 窗口一个 workgroup，16 wave，每 wave 一个 32 通道 head，替换生产的两核 `mh_attention_fused_fp8_out`（一头 4 wave，AV 字节写 global）+ `mh_attention_project_frag_c512`（裁切）/`mh_attention_project_fast_scalar_fp8`（identity）。
- 输入全是生产的：`mh_qkv_normalize_frag_c512` 的 FP8 [pixel][Q,K,V][512]、f32 FFN feature、`PackedMhWeightQkvFrag` 权重（不新增权重缓存）。
- 注意力核心（scores/exp/WMMA 行和/概率/AV）从 `hip/wave_owned_mh.inc` 原样拼接；AV 字节留在 32 KiB LDS。
- 投影保持生产的操作数方向（A=AV 行、B=权重片段）、K 0..511 顺序、`Hrtz(feature*scale)` 初值、post 0/3/4 尾部与裁切映射。
- 不挂 PDL（C512 链生产本来也不挂）。

## 结果

| | 900 | 1080 |
|---|---|---|
| C512 attention 调用/帧 | 13（42/43/46 默认跳过） | 13 |
| 一头一 wave，3 组 ABBA 配对差 | −0.0165 / −0.0219 / −0.0124，**均 −0.017 ms（−0.16%）** | −0.0126 / −0.0147 / −0.0293，**均 −0.019 ms（−0.12%）** |
| 正确性 | 12 槽首尾 + 16 动态帧全 bitdiff=0（含 identity 块） | 同 |
| 资源 | 124～125 VGPR、0 spill、LDS 32768 B、512 线程 | 同 |

差值落在同批噪声（约 ±0.02 ms）内，视为 null。

两 wave 共一头（`c512_attn_wave2`，1024 线程，各管 2 个 query tile）：撞 1024 线程的 192 VGPR 上限，110 个 VGPR 溢出、private 444 B；900 单轮 +0.30 ms，放弃。

## 奖金有多大：被替换两核的边际成本（重复派发，输出幂等，2 组 ABBA）

| 重复的核 | 900 | 1080 |
|---|---|---|
| `mh_attention_fused_fp8_out` | +0.173 / +0.157，均 **+0.165 ms** | +0.257 / +0.247，均 **+0.252 ms** |
| `mh_attention_project_frag_c512`（仅裁切块） | +0.225 / +0.217，均 **+0.221 ms** | +0.332 / +0.329，均 **+0.331 ms** |

两核合计约 0.39 / 0.58 ms（重复派发时第二次缓存更热，是下界近似）。融合核的耗时与之基本相等：省掉的 AV global 往返被并行度损失吃掉了。

## 为什么没赚

C512 在 1/16 分辨率，窗口少：900 只有 104 个窗口，1080 只有 135 个。融合后一窗口一 workgroup（16 wave、124 VGPR、32 KiB LDS），每 WGP 约 3 个常驻（12 wave/SIMD 的 VGPR 上限），32 个 WGP 一轮装 ~96 个，剩下 8（900）/39（1080）个排第二轮——尾巴长；每个 wave 还要串行做 4 个 query tile。生产两核各有上千个小 workgroup，没有这个尾巴。C64/C128 同样的改法赚约 20%，是因为那两层窗口多（上千个），并行度不是瓶颈。

要让融合在 C512 赚钱，得让一个窗口拆成更多并行单元而投影又需要全部 16 头的 AV（K=512），两者矛盾：拆 query tile 撞 VGPR 上限（上面的 wave2），拆头则投影要跨 workgroup。结论：C512 的 attention/projection 不走一头一 wave；这个族的时间主要在 FFN 链（mix → split FFN → split projection → QKV），下一步若继续 C512 应看那一段，而不是注意力。

## 文件

- 源：`Development/HIP/experiments/c512-wave/`（`c512_attention.inc` 内核、`prepare.py` 生成 /tmp/c512-wave 的 kernel.hip 与带 W2Mode 的生产 host 副本、`runner.cpp.in`、`build.ps1`、`run.ps1`）。host：`x86_64-w64-mingw32-g++-posix -std=c++17 -O2 -static -D_WIN32_WINNT=0x0A00 -I. network.cpp`。模块 gfx1201 base `7555FBAC…`，含 wave2 的 qs `CCC2F575…`（`build-manifest-*.json`）。
- 数据：`results-{900,1080}-base`（一头一 wave 全量）、`results-{900,1080}-qs`（重复派发诊断，模式 3/4）；`slots.csv`、`flags.txt`、`run-summary.log`（CONFIG/SLOT/VERIFY/DYNAMIC 行）。900-qs 目录里的 wave2 冒烟被后续诊断覆盖，数字记在本文。
- 生产源码、游戏安装、发布包均未改。
