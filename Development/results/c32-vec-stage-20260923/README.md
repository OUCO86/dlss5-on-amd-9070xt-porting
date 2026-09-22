# C32 f32 行输入的向量化 staging（mapped / post，2026-09-23，Hikari）

字节链那轮证明排队按请求数计。mapped（块首）和 post 读的是 f32 行（每 token 32×f32 = 128B），post 还带 4 字节 skip。原 staging：每 lane 16 条 b32 读 + 16 条 `ds_store_b8` + 16 条 `ds_store_b16`（in16）。改为：lane l 负责 token (l>>3)+4k（k=0..3）的通道 (l&7)*4..+3，4 条 `global_load_b128`（行索引经 `ds_bpermute` 从 lane 0..15 广播），Merge 再 4 条 b32 读 skip；4 个值算完打包一个 dword 写 `packed`，in16 两条 dword。每元素算式不变。基线 = 生产 + 字节链（prod3 等价）。三份相同变体 = 三份复现。

ISA（staging 段至首个 barrier）：mapped global_load 16→4、ds_store 32→8、VALU 247→189；post global_load 34→10（其中 b128 6）、ds_store 32→8、VALU 413→326。VGPR / 驻留不变。

整网 ABBA（每测试 8 槽 160 帧，逐位同，替换 1600/槽）：

| 档 | rep1 | rep2 | rep3 |
|---|---:|---:|---:|
| 1080 | −0.161 | −0.159 | −0.136 |
| 900 | −0.100 | −0.104 | −0.099 |

全部槽间分开。约整网 −0.9% / −0.8%，覆盖 post（97k wave）+ mapped×2（48k）。

采用：并入 `HIP_C32_BYTE_CHAIN`（同一开关，注释已更新）。prod4 = prod3 + 本项，10 核与实验 pair1 机器码逐条同。正式回归（候选 prod4，基线已装机的 prod2）见 deployments/stellar-prod4-20260923。

未做：prefix 核的 staging 是自己的路径（fused_prefix_values），96k wave，29% staging，下一处；生产者侧 16 条 `global_store_b8`/lane 未并。

证据：900/、1080/（network.csv、run.log、telemetry.log）、console.log。工具 HIP/experiments/c32-vec-stage。
