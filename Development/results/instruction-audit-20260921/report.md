# Explain the asymmetric performance signals — 2026-09-21

## Counted arithmetic versus issued work

The earlier727.8/1043.1GFLOP principal-matrix model explicitly omitted normalization/diagonal-emulation MMAs and scalar/memory work. Source audit identifies extra issued matrix operations: C32 Q/K and probability sums via16 identical output columns, local-attention denominator sums, ViT denominator sums, C32 chain diagonal residual matrices, MH16-channel diagonal residual tiles, and inline-prefix zero K padding.

Analytic addendum (same block/window geometry, not a full dynamic instruction census):
-900 additional25.60GFLOP FP8 +36.55GFLOP FP16; advertised-peak budget +0.253ms, total principal+known-extra matrix budget2.248ms.
-1080 additional36.66GFLOP FP8 +53.80GFLOP FP16; +0.370ms, total3.229ms.

Thus the earlier model was incomplete, but these known omissions do not explain~13/19ms runtime by a6x arithmetic-count error. Remaining scalar/conversion/address/control operations still are not represented by a TFLOP ratio. These reference budgets are not rigorously achievable frame times.

## Compiled ISA evidence

Current canonical MH source compiled on gfx1201 with production half/packed/hoist2 defines. C32 assembly is the adopted post-head-shared-input candidate, which matches current production source except comments. Static opcode/symbol inspection:

| Kernel | Static opcodes | WMMA opcodes | global_load_b64 | next_free_vgpr | LDS bytes | private bytes |
|---|---:|---:|---:|---:|---:|---:|
| C32 post/head fused |3013|58|34|217|19712|0|
| C128 mapped fused FFN/QKV byte stream |1758|72|80|108|10816|0|
| C256 mapped fragment FFN/QKV byte stream |2122|136|152|101|21568|0|

These are STATIC assembly counts, not dynamic instructions/time shares. Loop trips, lane masks, latency, instruction throughput and overlap matter. next_free_vgpr is compiler metadata, not rounded hardware allocation or measured occupancy. Private size0 gives no evidence of scratch spilling for these selected kernels, not proof all kernels never spill.

The point is structural: measured network time includes extensive conversion, clamp, packing, addressing, LDS/global accesses and dependency-management work around matrix instructions. High GPU busy and low principal-matrix TFLOPS can coexist. High L2 hits do not remove cache latency/instruction issue limits. Memory-unit busy is not DRAM bandwidth saturation. More core frequency can speed mixed instructions and their issue/consumption without proving that only matrix FLOPs are the bottleneck. These observations reconcile the signals, but do not assign all missing milliseconds to a measured single cause.

## Specific next hypothesis

The active C256 kernel has many64-bit loads. AMD's RDNA4 WMMA guide describes the same FP8/INT8 issue: native fragments are8 bytes/lane while vector memory instructions can load16 bytes. A real layout change can place two K16 B fragments adjacent for one128-bit load, followed by the original two MMAs. Merely moving source loads earlier gave identical machine code previously; changing stored fragment layout could alter the memory instruction width/count instead.

Proposed isolated trial: repack only C256 expansion weights at initialization as [N16][K32][lane][two8-byte fragments], use128-bit B loads, retain original K16 accumulation order and FP8 values, leave contraction/projection/QKV layouts untouched. Benchmark with matched host/kernel and exact-output controls; added registers/addressing can erase benefit. Do not call this implemented or proven yet. AMD's example usesINT8; integer associativity does not establish arbitrary floating-point reassociation safety, so preserve actual FP8 accumulation order explicitly.

Source: https://gpuopen.com/learn/wmma-guide-amd-rdna-4-gpus-part-2/ (especially layout/load-width discussion). Machine-readable static counts and arithmetic addendum are alongside this report; analyze.py reproduces from COMGR .hsaco.s files. No GPU benchmark/new game deployment in this audit.
