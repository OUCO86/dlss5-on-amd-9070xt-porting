# CU 模式按工作组大小逐核对照（2026-09-22，Hikari）

问题：fence-scope-all 里 C32（128 线程工作组）切 CU 模式赚 0.13～0.17ms，全模块切反而亏。是不是"128 线程就赚"的规律？

基线 = fence-modules（LDS 栅栏 + C32 CU，即当前生产）。三套候选只改 mh_fused / deep_fast / mh_fast，C32 沿用生产：

| 集合 | 改动 | 标记核数（mh_fused / deep_fast / mh_fast） |
|---|---|---|
| pair1 | 128 线程核加 target("cumode") | 3 / 4 / 20 |
| pair2 | 128 + 256 线程核 | 9 / 7 / 42 |
| pair3 | deep_fast 整模块 CU（复用 fence-scope-all pair2 的 deep_fast），其余生产 | — |

原计划 pair3 = 只切单 wave 核，mh_fused / deep_fast 编译报 always_inline 辅助函数与 WAVE 宏属性混编冲突（`always_inline function 'rc' requires target feature 'cumode'`），改为整模块。仅 gfx1201 编译（侦察实验，未做双架构）。

整网 ABBA，每测试 8 槽 160 帧，原始 FP32 逐位同，路由 218 次/帧：

| 档 | pair1 | pair2 | pair3 |
|---|---:|---:|---:|
| 1080 | +0.008 ms（交叠） | +0.051 ms（交叠） | −0.017 ms（交叠） |
| 900 | +0.027 ms（交叠） | +0.050 ms（不交叠） | +0.008 ms（交叠） |

核心频率两侧相同（±4MHz）。结论：CU 模式对其他模块的 128 线程核无收益，对 256 线程核轻微有害，deep_fast 整体无差别。C32 的收益来自它的结构（4 wave 间 LDS 密集交换 + 35KB 权重常驻 L0），不是工作组大小本身。此线关闭，生产不改。

证据：run1/{900,1080}/network.csv、run.log、telemetry.log；summary.json。工具 HIP/experiments/fence-cu-size/prepare.py，远端 D:\DLSSNR-Lab\hip-backend\fence-cu-size。
