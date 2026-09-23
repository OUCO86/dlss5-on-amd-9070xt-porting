# ffn_fused_c256 VGPR 封到 96（16 wave/SIMD），逐位同，反而慢 +0.06/+0.07ms，不采用（2026-09-23，Hikari）

起点：[launch 级驻留账](../launch-occupancy-20260923/README.md)——`mh_ffn_fused_c256_frag_project_*`（100～102 VGPR）驻留 12 wave/SIMD = 3 组/WGP，稳态并发 85～90%，尾 8～12%。16 wave 组按 4 wave/SIMD 递进，下一档 16 wave/SIMD 需 ≤96 VGPR。

改法：`amdgpu_waves_per_eu(16,16)`。regex 只命中 512 线程核，所以实际只有两个 c256 frag 核被封（c64 是 128 线程、c128 是 256 线程，未改）；三份 pair 集内容相同 = 三份复现。编译结果：两核 96 VGPR、各溢出 8/9 个寄存器到 scratch（`private_segment_fixed_size` 非零 8 处）。

整网 ABBA（模块集 host，每测试 8 槽 160 帧，逐位同）：

| 档 | rep1 | rep2 | rep3 |
|---|---:|---:|---:|
| 1080 | +0.055 | +0.061 | +0.057 ms（+0.3%） |
| 900 | +0.083 | +0.060 | +0.072 ms（+0.6%） |

核心频率两侧相同（2735/2758 MHz 中位）。

读法：驻留 +33% 换不回 8～9 个寄存器的溢出往返——这个核在 12 wave 时延迟已经盖住（稳态并发贴顶、阶段账里等待主要是 barrier 和 LDS 中转，不是取数延迟），多加的 wave 只是多排队。与 C32 in16 别名（+33% 驻留只换 4%）同一结论的反面样本：**驻留只在它是瓶颈时值钱**。此线关闭。

证据：1080/、900/ 下 network.csv、run.log、telemetry.log；console.log。工具 HIP/experiments/mhfast-vgpr-cap。
