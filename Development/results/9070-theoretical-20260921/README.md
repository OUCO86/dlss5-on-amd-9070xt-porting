# RX9070XT peak vs this network — 2026-09-21

Official AMD product specifications accessed2026-09-21:
https://www.amd.com/en/products/graphics/desktops/radeon/9000-series/amd-radeon-rx-9070xt.html
64CU, up to2.97GHz boost; FP32 vector48.7TFLOPS; dense FP16 matrix195TFLOPS; dense FP8/INT8 matrix389TFLOPS/TOPS; sparseFP8/INT8 779; denseINT4 779TOPS; sparseINT4 1557;16GB GDDR6, up to640GB/s,64MB Infinity Cache. Peaks are advertised boost-rate capacities, not measured frequencies/power or guaranteed sustained rates.

estimate.py is an analytic principal-matrix model, not GPU hardware counters. It follows current host block counts, processing1600×960/1920×1152,64-token local windows, shift padding,400/640ViT tokens, grouped MH contraction128K and splitC512 FFN groups, skip42/43/46, reuseoff. Counts2 operations/MAC. Includes dominant FFN/QKV/projection/QK/AV/down/up matrices and small input/RGB heads. FP16 assigned to C512 mix/expansion, ViTQKV, down/up and input head; other principal matrices FP8, RGB dot FP32. post_shift3, confirmed from NativeGameFrame::Create; corrected after the pure-HIP control audit. The correction changes the principal estimate by less than0.1%; older rounded figures below retain the original calculation context.

Excluded: normalization/activation and other scalar arithmetic, diagonal residual-emulation MMAs, instruction-level duplicated lanes/zero arithmetic beyond the model, codec/resampling, memory traffic, synchronization and CPU/driver work. Cropped/padded kernel details can change exact issued counts. Thus round estimates, not exact totalFLOPs or hardware utilization. No DRAM-byte counters available; do not invent achieved bandwidth or idle percentage.

Results:
-900 principal matrices≈727.8GFLOP/frame; measured whole-replay baseline13.2069ms →≈55.1TFLOPS effective,14.2% of denseFP8 peak. Mixed-rate idealized matrix budget≈1.995ms, actual/ideal≈6.62.
-1080≈1043.1GFLOP/frame;18.6881ms →≈55.8TFLOPS,14.3% of denseFP8 peak. Mixed-rate idealized budget≈2.859ms, ratio≈6.54.

Timing source: ../ffn-expand-prefetch-20260921/summary.json baselineABBA means (includes existing RGB-head improvement, full replay overhead, no game rendering, no reuse). This is not the user's displayed gameFPS. Mixed-rate budget sums F8/389+F16/195+F32/48.7 at advertised peaks; omitted work and overlap mean it is a reference budget, not a rigorously established achievable runtime or promised6.5x optimization.

Concrete operator cross-check: actual tested block31 expansion M400 K1024 N4096 has exactly3.3554432GFLOP of dense matrix multiplication. About34.5µs including pack/activation/output gives97.3TFLOPS matrix-work-per-total-time (~25% of FP8 peak). Bare matrix ideal at389TFLOPS is8.626µs,4x below observed complete-operator time. Sparse2:4 test was20.4µs but prunes half the weights and is not comparable as an unchanged workload; it is not deployed.

Interpretation: substantial distance from ideal matrix throughput remains, but neither15% equivalent compute efficiency nor100% GPU busy indicates actual ALU occupancy or removable waste. Narrow/grouped matmuls, dependencies, conversions, barriers, LDS and data movement consume the elapsed time. Next useful evidence is instruction/resource profiling and measured DRAM/cache traffic, not just comparing advertised sparseTOPS to dense workload.
