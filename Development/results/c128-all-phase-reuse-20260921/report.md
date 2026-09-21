# C128 whole-pipeline row reuse: three exact-output probes

No production adoption. The all-phase variant gives a small benefit but has not demonstrated an improvement over the previous balanced-expansion-only candidate. Hybrid and compact variants lose isolated-kernel time and are rejected. No game DLL/package was changed.

## Measured results

| Variant | Baseline → candidate μs, full fused kernel | Change |
|---|---:|---:|
|256 threads, two rows per wave in every phase|90.41170 → 88.83035|1.75% faster|
|512 threads, balanced expansion then8 active waves|90.88725 → 97.01235|6.74% slower|
|256 threads, compact16KiB swizzled arena|90.17830 → 102.38175|13.53% slower|

Each row is its own ABBA with2000warmup/10000measured launches on the real first mapped C128 input/weights, unprofiled pureHIP, host wall/sync timing. All24 first/final raw FP32 network comparisons have bitdiff0. These are hot repeated-kernel results, not game frame attribution.

The first variant also passes96 paired720/900/1080 RGB frames, static/motion/history/f32input/f32feature routes, with unchanged full-frame hashes. Final1000frame ABBA discards200:900P13.308555→13.289774ms, saves0.018781ms;1080P18.837043→18.801353ms, saves0.035689ms. Short160frame ABBA saves0.009152/0.045633ms. The prior candidate saved~0.030/0.054ms with~2.76% isolated-kernel gain in its own ABBA. Cross-run drift prevents treating these tiny differences as a strong ranking, but this does not establish a new winner. Slower hybrid/compact did not receive unnecessary broad RGB/game tests.

## A more precise residency bound

| Variant | Threads/group | LDS bytes/group | Actual VGPR | Assembly Occupancy | Runtime active groups/MP | Resident wave bound/MP |
|---|---:|---:|---:|---:|---:|---:|
|Original|256|10816|108|12|6|48|
|Prior expansion-only|512|21632|103|12|3|48|
|All phases|256|21632|124|10|3|24|
|Hybrid|512|21632|101|12|3|48|
|Compact|256|16384|94|16|4|32|

The local runtime reports warpSize32,32 multiprocessors,2048max threads/MP,65536shared bytes/MP. Use these runtime units as reported; do not reinterpret the32 MPs as the advertised CU count. The block/LDS-aware API returns a theoretical active-block bound, not actual observed occupancy. ABI/method: [AMD HIP7.1.1 runtime API](https://github.com/ROCm/HIP/blob/rocm-7.1.1/include/hip/hip_runtime_api.h#L6646-L6657).

This identifies a real counterweight to reuse: the all-phase layout halves resident wave capacity. The original and prior candidate both permit48; simply comparing register counts or the compiler's Occupancy comment missed this. Hybrid nominally restores48 slots, but only half its waves work in later phases. Compact raises the all-phase bound24→32 and lowers registers, yet slows down. Thus residency improvement is not sufficient. The exact shares due to synchronization, address operations, scheduling and LDS bank behavior have **not** been individually measured.

## Implementation and interpretation

All-phase keeps the original per-outputK order and exact activation/rounding boundaries. Expansion has8accumulators per wave, contraction/projection/QKV have2, sharing each weight fragment over two16-row tiles. Relative to the original wave it computes twice the output:144WMMA vs72,88static64-bit global loads vs80. Since group count halves, this is a substantial normalized load-instruction reduction, not an88-vs80 regression. Static counts are still not DRAM-byte or elapsed-time measurements.

Hybrid retains the lighter expansion but runs later phases on half its512threads. Compact reuses storage by lifetime, uses an XOR swizzle for the32×512-byte expansion, and normalizes row tiles sequentially to fit feature/raw/inverse scratch into the same16KiB allocation. This adds a projection handoff barrier and more executed normalization barriers. Its compiler leaves some loops in ISA, so7static barrier pairs/112WMMA must not be interpreted as fewer dynamic barriers/operations than the all-phase8/144. All three scratch sizes are0.

Conclusion: save the first candidate as research, reject the two slower controls, retain the prior balanced-expansion candidate. The next useful experiment should isolate the cost of cross-wave LDS exchange/normalization from the matrix phases while keeping equal-output controls; another blind increase in row reuse or occupancy is not justified. Phase-omission probes, if used, are diagnostics only and cannot be reported as image-preserving speedups.

Evidence: per-variant summary.json, CSV/flags/frame hashes/kernel logs/artifact hashes; isa.json; occupancy.txt. Both gfx1200/gfx1201 compile, execution on gfx1201 only. Production definitions include HIP_PREPACKED_WEIGHTS=1. The three experimental modules must be paired with their documented launch geometry.
