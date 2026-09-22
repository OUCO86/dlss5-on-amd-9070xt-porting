# mh_fused C64/C128/C256 注意力段 ex/prob 寄存器化（2026-09-23，Hikari）

起点：mh-phase-trace 显示 c256_attention_project 每段都比指令数慢约十倍，LDS 每组 59.6KB（all_ex 33.8KB + V 9.2KB + avbytes 16.6KB）把驻留压到每 SIMD 4 个 wave。C32 上同样的寄存器化因 VGPR 压力没赚，这里驻留是 LDS 限制的、VGPR 只有 131，正好对症。

**改法**（三个函数体同一补丁）：分数 WMMA 对调操作数得 D^T，每 lane 持自己查询行的 8 个连续 key；两侧行和用"全 1 矩阵"对调后的 WMMA 直接得每 lane 行和（partial0/partial1 分组不变）；prob 在寄存器打包成 AV 的 A 片段。`all_ex` 删除；c64/c128 原把 `avbytes` 别名在 `all_ex` 上，改为独立小数组（64×68 / 64×132）。每批 6 个同步剩 2 个（V staging 后、批末）。每元素算式不变。

**ISA**（isa-markers.txt）：LDS c64 21.5→9.0KB、c128 43.0→17.7KB、c256 59.6→25.9KB；编译器驻留 12/12/8 → 16/16/12；LDS 指令 161～173 → 85～97；barrier 6→2；VGPR 89/103/131 → 92/92/118。

**整网 ABBA**（fence-scope-all 模块集 host，每测试 8 槽 160 帧，逐位同）：

| 轮 | 范围 | 1080 | 900 |
|---|---|---:|---:|
| r1 | 仅 c256 | −0.074 / −0.072 / −0.072 | −0.045 / −0.052 / −0.038 |
| r2、r3 | 仅 c256（prepare 失败误跑，等于复现） | −0.061 / −0.060 / −0.055；−0.061 / −0.040 / −0.055 | −0.056 / −0.053 / −0.043；−0.046 / −0.050 / −0.038 |
| **r4** | **c64 + c128 + c256** | **−0.184 / −0.165 / −0.159** | **−0.119 / −0.127 / −0.109** |

全部槽间分开。约整网 −1.0%。

**采用**：`HIP_MH_REGISTER_EX`（默认 1）进 hip/multihead_fused_attention.hip，三个函数体各处以 #if/#else 包住；prod5 = prod4 + 本项，22 核与实验机器码逐条同。正式回归见 deployments/stellar-prod5-20260923。

**未做**：`mh_attention_fused_fp8_out`（C512 注意力，13 次/帧，结构不同，自己的 ex/packed，3 个同步）；mh_fast 的 ffn_fused 与 C512 单 wave 核未打点。

证据：r1/、r4/（900、1080 各 network.csv、run.log、telemetry.log）、console 日志、isa-markers.txt。工具 HIP/experiments/mh-register-attention（prepare.py），远端 D:\DLSSNR-Lab\hip-backend\mh-register-attention。
