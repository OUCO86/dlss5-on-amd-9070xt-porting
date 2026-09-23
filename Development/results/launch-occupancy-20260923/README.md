# launch 级驻留与尾巴账（2026-09-23，Hikari）

核内阶段账（c32/mh/mhfast-phase-trace）是每 wave 的；这一层是每 launch 的：每 wave 记入口/出口两个 64 位实时戳（`__builtin_readsteadycounter` = `s_sendmsg_rtn REALTIME`，100MHz）和 `HW_ID1`（SE/SA/WGP/SIMD），由此得到每个 launch 的 span、并发曲线、爬坡/稳态/尾巴，以及每个 SIMD 上同时驻留的 wave 数。三个已有打点核，prod5 模块基线，8 帧，逐位同。工具 HIP/experiments/launch-occupancy，原始 trace 未入库（1.3GB），analysis.txt 为全部 launch 的表。

## 先纠一个前提

9070 XT 是 32 WGP × 4 SIMD32 = **128 个 SIMD**，不是 256。之前 C32 阶段账里"有效并发 3.3/6"的分母算错了。HW_ID 直接数出来的驻留：

| 核 | LDS/组 | VGPR | 模式 | 实测峰值 wave/SIMD | 组/CU（或 WGP） | 上限来源 |
|---|---:|---:|---|---:|---|---|
| C32 chain/finish/prefix（7 核） | 15360 | 151～172 | CU | **8** | 4 组/CU | LDS：4×15360 = 61440 ≤ 64KB |
| C32 mapped / post_merge（3 核） | 19712 | 153～169 | CU | **6** | 3 组/CU | LDS：3×19712 = 59136；第 4 组放不下 |
| mh_fast ffn_fused_c256 | 21568 | 102 | WGP | **12** | 3 组/WGP | VGPR（12 wave/SIMD） |
| mh_fused c256_attention（寄存器版） | 25856 | 118 | WGP | **12** | 3 组/WGP | VGPR |

CU 模式下每 CU 可用 LDS 是 64KB（128KB/WGP 的一半），C32 的驻留完全由 LDS 决定，VGPR 还有余量（1536/176 ≈ 8.7）。

## 每 launch 的账（1080，900 同形；单位 μs）

| 核 | launch/帧 | span 合计 | 吞吐时间（busy/槽位） | 稳态并发/槽位 | 爬坡 | 尾巴 |
|---|---:|---:|---:|---|---:|---:|
| C32 十核 | 10 | 5557 | 4823（87%） | chain 980/1024（96%）；mapped/post 735/768（96%） | 12（0%） | 43（1%） |
| ffn_fused_c256 | 12 | 984 | 861（87%） | 1300～1380/1536（85～90%） | 29（3%） | 81（8%） |
| c256_attention | 14 | 569 | 401（70%） | 1030～1170/1536（67～76%） | 25（4%） | 143（25%） |

900：C32 3790/3279（87%）、ffn_fused 872/750（86%，尾 12%）、c256_attention 467/293（63%，尾 37%）。

读法：

1. **C32 没有 launch 级损失**：爬坡+尾巴 1%，稳态并发贴着 LDS 上限（96%）。它的缺口全在核内（阶段账那些）。但 mapped/post 三个核比其他七个少一组/CU——post_merge_head 是整网最大的单个 launch（1080 下 1.46ms，占 C32 的 26%），加上两次 mapped 共 2.17ms，都跑在 6 wave/SIMD 而不是 8。
2. **ffn_fused_c256 稳态离 VGPR 上限还有 10～15%**，尾巴 8～12%：每 launch 只有 2～3 轮组，最后一轮填不满。
3. **c256_attention 尾巴 25～37%**：每 launch 104～160 组、每组 17～20μs，总共 2～2.5 轮，最后半轮全网空转。14 次/帧合计 0.14～0.17ms 是纯尾巴。寄存器版把 LDS 从 59648 减到 25856，驻留从 4 升到 12 wave/SIMD（VGPR 封顶），但组数没变，轮数从 4～5 降到 2～2.5，尾巴占比反而更显眼。

## 下一刀

- **C32 in16 别名到 Scratch**（c32-lds-alias）：in16 只活到残差初始化，Scratch 到 QKV 归一化才首写，中间两个 sync_window；别名后三核 LDS 19712→15360，驻留 6→8。逐位按构造相同。
- c256_attention 的尾巴要么减组时长（组内 16 wave 已是两批 head，改 4 批组数翻倍每组减半），要么让相邻两个独立 launch 并发（同 stream 做不到，需要第二 stream + 事件，host 侧改动）。
- ffn_fused_c256：VGPR 102→≤96 可到 16 wave/SIMD（+33% 槽位）——已试（[mhfast-vgpr-cap](../mhfast-vgpr-cap-20260923/README.md)），溢出 8～9 个寄存器，反而 +0.06/+0.07ms，关闭。
- c256_attention 的第二 stream 想法作废：host 里每次注意力前后是同一条链上的 ffn_fused（产 norm→注意力→下一块 FFN），没有可并发的兄弟 launch。尾巴是结构税。

## 限制

- 每个打点 launch 前 host 同步一次流（为写 trace 基址），launch 是孤立跑的；正常流水线里相邻 launch 也不重叠（同 stream），但前一个 launch 的尾巴和下一个的爬坡在真实运行里也许有少量重叠，这里量不到。
- HW_ID1 按 gfx11 位域解（WAVE[4:0] SIMD[9:8] WGP[13:10] SA[16] SE[20:18]），128 个 SIMD、32 个 WGP 全部出现，与硬件规格一致，视为解对了。
- 打点核比生产核多约 30 条指令和 16 个 u64 写，span 略长于真实。
