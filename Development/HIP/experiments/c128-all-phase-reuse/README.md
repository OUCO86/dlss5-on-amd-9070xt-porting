# C128 row reuse across all fused phases

Experimental C128 row-major FFN/QKV body. A 256-thread workgroup covers 32 rows. Every wave processes two 16-row fragments and shares each B fragment between them in expansion, grouped contraction, residual projection and each QKV projection. Weights, activation and per-output K accumulation order are unchanged. Normalization still sums the same 32 squared values in order. The LDS raw layout is [head][32 rows][33 floats].

Expansion owns M32×N64 per wave (8 accumulators); contraction/projection/QKV own M32×N16 (2 accumulators). This deliberately trades register/residency pressure against more weight reuse; compare it with the prior balanced-expansion-only candidate, not just the standalone expansion microbenchmark.

`prepare.py` emits a standalone host/module in `/tmp/c128-all-phase-reuse`. Build generated benchmark.cpp with the normal HIP MinGW command as benchmark_c128_all.exe. The module prepends all production defines, including HIP_PREPACKED_WEIGHTS=1. `build.ps1` compiles gfx1200 and gfx1201; runtime tests are gfx1201 only. Six C128 entries get isolated routing; fragment/tiled/batched norm alternatives are unchanged. This experiment reuses the `_m32` suffix but uses **256** threads; the prior c128-fused-row-reuse used 512. Never mix their runners/modules.

`run.ps1`: 48 paired static/moving RGB frames at 900/1080 then ABBA160. `-TimingOnly -TimingFrames 1000`: long ABBA, discard200. `-ExtraControls`:720, temporal history, float input and float feature output. `prepare-timing.py` replaces the temporary host with the pure-HIP repeated-kernel harness; compile pure.cpp as pure_c128_all.exe, run time-kernel.ps1 for 2000warmup/10000measured ABBA and raw FP32 output controls. Re-run prepare.py to restore the ordinary host. Do not use the timed host for normal network measurements.

All GPU scripts guard known games/Magpie. Production kernels, game DLLs and packages are unchanged.

Two further controls:

* `prepare-hybrid.py` / `build-hybrid.ps1`:512-thread balanced M32×N32 expansion, then only the first8waves execute dual-row contraction/projection/QKV. All16waves reach every barrier. Uses the previous benchmark_c128_m32.exe and pure_c128_m32.exe (512-thread dispatch) with its own module directory.
* `prepare-compact.py` / `build-compact.ps1`:256 threads, one16KiB shared arena. Expansion addresses use row*512 + (channel XOR ((row&15)*8)), keeping each8-byte fragment contiguous. After contraction/projection reads finish, feature storage reuses the arena; normalization uses separate offsets inside it and processes the two row tiles sequentially with the original32-term sums. Uses benchmark_c128_all.exe/pure_c128_all.exe. Source barrier executions increase even though some loops remain in ISA, so static instruction counts are not directly dynamic totals.

Both slower controls were rejected after pure-HIP raw-output checks and isolated ABBA; no broad RGB/whole-network timing was run for them. First all-phase variant has96 paired RGB frames plus160/1000frame ABBA. `collect.ps1 -Experiment <directory-prefix>` archives each variant. `analyze.py <evidence> --kernel-only` explicitly permits the rejected probes to omit RGB controls.

`occupancy.cpp` queries the runtime's predicted active blocks for the actual module/function/block-size combination, not measured live occupancy. Compile standalone, pass `D:/DLSSNR-Lab/hip-backend`. Its runtime API gives48 resident wave slots for the old kernel,24 for256-thread all-phase reuse,48 for hybrid (but half inactive in later phases),32 for compact. Do not substitute the assembly's register-derived Occupancy comment for this block/LDS-aware bound. Decision/report: `Development/results/c128-all-phase-reuse-20260921/report.md`.
