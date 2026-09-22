# ViT 融合注意力：寄存器化 + V 转置（2026-09-23，Hikari）

`vit_attention_fused_{400,640}_bytein`（8 次/帧，单 wave 工作组，32 头 × token/16 个 wave）。每个 key tile：分数 WMMA → 仿射/半精度编码写 LDS → barrier → 读回转置 → 行和 WMMA + AV。400 token = 25 个 tile = 每 wave 25 个 barrier。

**r1 寄存器化**：分数 WMMA 对调操作数，读回的片段直接来自寄存器，行和与 AV 代码不变；t16 与 26 个 barrier 全部去除。逐位同。整网 1080 −0.019/−0.021/−0.010ms、900 −0.011/−0.014/−0.002，全部交叠——单 wave 组的 barrier 本来就便宜。ISA：每 tile 16 条 `global_load_u8`（V 聚集）+ 4 条 b64，VGPR 72，驻留 16。

**r2 + V 转置**：QKV 投影核 part 2 改写为 [head*32+col][key]（一条 8B 写代替 8 条散字节写），AV 的 B 片段变一条 8B 读（每 wave 400 条字节读 → 50 条）。首轮只改了 `HIP_VIT_HOIST_SCALE` 分支（默认 0，未编译）导致输出不符，两分支同改后逐位同。整网 1080 −0.030/−0.025/−0.032ms、900 −0.012/−0.021/−0.023，多数交叠。

结论：这个核太小（每 launch 800 wave、约 5 个 WMMA/tile），去掉 LDS、barrier、350 条读请求加起来只值 0.02～0.03ms。**不采用**（V 布局改动影响共享张量，收益不够）。反例价值：请求数规律对"本来就短"的核不成立。

证据：r1/、r2/。工具 HIP/experiments/vit-register-attention。
