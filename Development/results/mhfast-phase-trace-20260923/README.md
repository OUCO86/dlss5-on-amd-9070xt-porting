# mh_fast `mh_ffn_fused_c256_frag_project_mapped_g128_qkv_bytein_fb` 每 wave 阶段账（2026-09-23，Hikari）

15 次/帧、512 线程（16 wave/组）、每 launch 416 组 6656 wave（有效 6240）。打点：入口、展开循环后、激活+hidden 写后、收缩后、结束；8 个裸 `s_barrier` 全部计时。8 帧，逐位同。

**注意**：这个核走 ByteIn 路径，没有独立的输入 staging 段（输入在展开循环里直接读），analysis.txt 的"input staging"一栏无效（t[1] 未写入产生负数），应与"expand"合并。

每 wave 约 33.3k 周期（15 次 launch 一致）：

| 段 | 周期 | 份额 |
|---|---:|---:|
| 输入读 + 展开（64 WMMA） | ~10.4k | ~31% |
| 激活 + hidden 写 | 4.1k | 12% |
| 收缩（Grouped：每 wave 128 个 k） | 4.2k | 12.6% |
| 投影 + QKV（3 部分）+ 归一化 + 输出 | 14.7k | **43.5%** |
| 其中 barrier 等待（8 次/wave） | 6.4k | 19% |

ISA：2237 条指令，136 WMMA（约 2.2k 周期，7%），162 条 global_load（权重片段 8 字节一条 + 输入字节），41 条 global_store（out 8 条 b8 + norm 24 条 b8 + ...），166 条 LDS，VGPR 102，驻留 12，LDS 21.6KB。

读法：矩阵 7%，其余是取数、LDS 中转和 8 个 barrier。尾段 43% 里：投影 16 WMMA + 残差 8 次输入读 + QKV 48 WMMA + 两次 LDS 往返（归一化的平方和由 256 线程串行 32 循环完成）+ 3 个 barrier + 32 条散的字节写。

候选方向（按 C32/ViT 的规律）：权重片段读 8B→16B 并请求（162→~90）；out/norm 字节写并成 dword（需转置布局，但归一化平方和的串行求和顺序不能变）；barrier 19% 里能省的看依赖。

证据：900/analysis.txt。工具 HIP/experiments/mhfast-phase-trace。
