# C32 注意力段 ex / prob 寄存器化（2026-09-22，Hikari）

同折叠 FFN 的手法推到注意力：分数 WMMA 对调操作数得到 D^T，每 lane 持一行查询 × 8 个连续 key，正是行和 WMMA 与 AV 所需的 A 片段；行和那个"乘全 1 矩阵"也对调，输出每 lane 直接是自己行的和，不需要跨 lane 搬运。ex（原 64 条 ds_store_b16 + 读回）与 prob（原 32 条 ds_store_b8 + 读回）全留寄存器；K、V 跨 wave 共享仍在 LDS。基线 = 当前生产（LDS 栅栏 + C32 CU 模式 + 折叠 FFN）。

| 变体 | 同步 |
|---|---|
| pair1 | 四处 ATTN_SYNC 全保留 |
| pair2 | 分数后、prob 后两处删除（prob 不再覆盖 packed，原 barrier 的理由消失）；AV 写回 packed 前后两处降为 wave 内栅栏 |
| pair3 | 同 pair2，但投影前那处保留全组同步 |

**逐位**：三变体两档 24 槽全同（含"乘 1 矩阵"对调）——WMMA 对两个操作数角色的累加顺序对称，这一点已被 FFN 与注意力两处独立验证。

**ISA（post 核）**：LDS 指令 401→324，ds_store_b16 64→32，ds_store_b8 128→96，barrier 8→4（pair2）；但 **VGPR 158→226**，chain 核驻留 8→7。

**整网 ABBA（每测试 8 槽 160 帧）**：

| 档 | pair1 | pair2 | pair3 |
|---|---:|---:|---:|
| 1080 | +0.060（交叠） | −0.040（交叠） | −0.042 |
| 900 | +0.041 | −0.039（交叠） | −0.019 |

结论：机制成立、逐位同，但寄存器压力抵消了 LDS 与 barrier 的节省——原先 LDS 兼作溢出区。净收益 ≤0.04ms、与噪声交叠，**不采用**。

后续若要救：exfrag[4]+pfrag[4] 只占 24 VGPR，多出的约 45 是编译器调度（V 字节聚集与分数计算重叠）所致；可试 `amdgpu_waves_per_eu` 限压、或按 key tile 流水（分数 tile → 行和累加 → 只保留 ex 位）。仅 gfx1201/gfx1200 各编一次，单轮。

证据：r1/{900,1080}、console.log、isa-markers.txt。工具 HIP/experiments/c32-register-attention，远端 D:\DLSSNR-Lab\hip-backend\c32-register-attention。
