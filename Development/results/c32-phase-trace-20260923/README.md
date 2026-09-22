# C32 每 wave 阶段周期账（核内时间戳，2026-09-23，Hikari）

账本里"还没量"的第一项：C32 各阶段的动态时序。之前只有静态发射预算和不可信的短段 host 事件。这次在三个热核的共享函数体里，每个 wave 在 9 个阶段边界读 `SHADER_CYCLES`（`__builtin_readcyclecounter`，gfx12 落成 `s_getreg HW_REG_SHADER_CYCLES`），并把每次 `sync_window`/`sync_owned_rows` 内部的周期累加为"barrier 等待"；结束时 lane 0 写 12 个 u64 到全局缓冲。缓冲基址放在模块全局变量 `c32_trace`，host 在每次 C32 launch 前用 `hipModuleGetGlobal` + `hipMemcpy` 写入，核签名不变。30 帧预热后连续 8 帧全部 C32 launch 打点，缓冲保留最后一帧；网络原始 FP32 与期望逐位相同（打点不改结果）。基线 = 当前生产（LDS 栅栏 + C32 CU + 折叠 FFN）。

首轮 1080 越界（缓冲按 900P 的 24321 组开，1080 post 有 34945 组），改 40000 组后两档通过。

## 全 C32（10 次 launch，按 wave-周期加权），900P / 1080P 几乎相同

| 阶段 | 份额 |
|---|---:|
| 输入 staging（gather + FP8 + 写 packed/in16） | **30.7%** |
| FFN 展开+收缩（折叠版） | 26.1% |
| FFN 写回 + 同步 | 3.9% |
| QKV 投影（3 部分 + 归一化） | 10.8% |
| 分数 | 4.7% |
| softmax / prob | 4.4% |
| AV | 2.7% |
| 投影 / 输出 | 7.9% |
| 尾部（finish / RGB / down） | 8.8% |
| 其中 barrier 等待 | 8.7% |

## 逐 launch（900P，每 wave 周期均值；1080P 同量级见 1080/analysis.txt）

| launch | 核 | waves | 总周期 | staging | ffn | qkv | 注意力三段 | 投影 | 尾部 | barrier 等待 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | prefix_finish_main8 | 96000 | 29,693 | 8,576 | 6,711 | 2,836 | 3,560 | 1,789 | 4,741 | 3,530（10 次） |
| 1 | mapped | 24000 | 21,004 | 5,281 | 6,569 | 2,888 | 2,844 | 2,615 | 82 | 1,413 |
| 2/3/6/7 | chain | ~24.5k 各 | 25,480 | 8,380 | 7,470 | 2,915 | 2,905 | 2,695 | 88 | 2,205 |
| 4 | chain_finish_dcrop | 24400 | 29,891 | 8,086 | 7,894 | 2,846 | 3,439 | 1,717 | 4,899 | 2,121 |
| 8 | chain_finish | 24400 | 28,110 | 7,891 | 7,540 | 2,854 | 3,134 | 1,782 | 3,894 | 2,058 |
| 9 | post_merge_head | 97284 | 23,643 | 8,057 | 5,820 | 2,666 | 2,779 | 1,585 | 2,068 | 1,571 |

p90 与中位数接近，分布窄（见 analysis.txt）。

## 读法

- **输入 staging 是 C32 最大的单项**，每 wave 8k 周期。它做的事：16 行 × （readlane 取索引 → 全局读 fp32/f16/fp8+skip → FP8 转换 → `packed` 字节写 + `in16` 半精度写）。以 post 为例矩阵指令全算上约 1.1k 周期，staging 是它的 7 倍。这和 kernel-bottleneck 捕获的 memory unit busy 99% 吻合：向量内存管线被输入读取和 LDS 字节写占满。
- FFN 26% 里矩阵本身约 0.5k 周期，其余是权重取数、激活、打包。
- 注意力三段合计 11.8%，之前寄存器化那刀瞄的是这块的 LDS，本来就不大——解释了为什么收益 ≤0.04ms。
- barrier 等待 8.7%（prefix 10 次、其余 8 次），已经是栅栏改 LDS 作用域之后的数。
- 尾部（RGB / 下采样输出）在三个 finish/prefix/post 核里 9～16%。

对账：post 97284 wave × 23.6k 周期 ≈ 2.3G wave-周期；256 个 SIMD 串行需 9.0M 周期，按 ~2.7GHz 约 3.3ms，实测 post 约 1.0ms → 有效并发约 3.3 个 wave（驻留上限 6）。这就是"四条管线本该重叠却接近串行"的动态版：延迟掩盖只有一半。

## 下一步（按份额）

1. staging：让上游核直接输出 FP8 字节（chain/post 的输入是 f16/f32，读 4 倍字节再转换）；staging 的 `packed` 字节写改 dword（INPUT_DWORD 路径只在非 LANE_STAGE 分支）。
2. FFN 里的权重取数与打包。
3. 尾部输出。

## 边界

- 时间戳是 wave 自己的时间线，包含被其他 wave 抢占/交错的时间；份额是"wave 生命周期"而不是"SIMD 忙碌"。
- 只保留最后一帧；未做 Graph、未做多次重复。
- 原始 trace（每档 10 个 u64 文件共 294MB）未入库，sha256 在 trace-u64-sha256.txt，本地 /tmp/c32-phase-trace/ev，远端 D:\DLSSNR-Lab\hip-backend\c32-phase-trace\{900,1080}。

工具 HIP/experiments/c32-phase-trace（prepare.py 生成打点核与 host，analyze.py 统计）。
