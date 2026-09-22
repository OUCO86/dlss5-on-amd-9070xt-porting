# mh_fused c256_attention_project 每 wave 阶段账（2026-09-23，Hikari）

C32 的核内时间戳搬到 mh_fused `c256_attention_project_fb_bout_diag`（14 次/帧，512 线程 = 16 wave/组）。host 只路由这一个核名到 `_pair1` 变体，缓冲基址经模块全局 `mh_trace`。8 帧打点，逐位同。

**注意**：函数体内 `batch` 循环跑两次（8 个 head 分两批），打点在第二批被覆盖，所以 analysis.txt 里"V staging"一栏 = 第一批全部 + 第二批 staging。换算：两批注意力（V staging→avbytes）约 42%，残差/对角 21%，投影+输出 17%，barrier 等待 12%（每 wave 12 次）。每 wave 约 50k 周期。

关键判断：前奏到首个 barrier 只有 233 条指令，而各段都比指令数慢约十倍——LDS 59.6KB/组 → 每 CU 一组 → 每 SIMD 4 wave，延迟盖不住。这直接引出 mh-register-attention。

证据：900/analysis.txt、trace-groups.txt（原始 trace 未入库）。工具 HIP/experiments/mh-phase-trace。
