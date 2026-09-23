# 注意力残差特征读提前到核入口，逐位同，反而 +0.07～0.12ms，不采用（2026-09-23，Hikari）

起点：c256 注意力阶段账（LDS 版）里"残差/对角"占 21%——最后一个 sync 之后才发出的特征片段读（c256 每 lane 4 条 8B，c64/c128 2 条）冷读，对角 WMMA 链等它。改法：这些读在核入口就发出，寄存器里留着（c256 +8 VGPR：118→122；c64/c128 92→94，驻留都还是 12 wave/SIMD），同一批字节，逐位同。pair1 只改 c256，pair2 三核都改，pair3 = pair1。

整网 ABBA（模块集 host，每测试 8 槽 160 帧，bitdiff 0）：

| 档 | pair1 c256 | pair2 三核 | pair3 c256 |
|---|---:|---:|---:|
| 1080 | +0.092 | +0.116 | +0.067 ms |
| 900 | +0.044 | +0.084 | +0.055 ms |

核心频率两侧相同。

读法：那 21% 是 LDS 版（4 wave/SIMD）时的账；寄存器版 12 wave/SIMD 已经把这段延迟盖住了，提前发出的读反而和入口的 packed staging 抢队列，把第一段拖慢。**阶段账要在当前驻留下重打，不能沿用旧版的份额。** 此线关闭。

证据：1080/、900/ 下 network.csv、run.log、telemetry.log；summary.txt；console.log。工具 HIP/experiments/mh-hoist-residual。
