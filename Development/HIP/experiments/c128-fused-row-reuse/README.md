# C128 M32×N32 expansion inside fused FFN/QKV

Isolated candidate; production source, game DLLs and release packages are unchanged.

`prepare.py` copies the current host into `/tmp/c128-fused-row-reuse`, appends a specialized body to the current multihead source, and emits `kernel.inc` for review. New `_m32` entry points use 512 threads / 32 rows. Only the six compatible C128 row-major, sequential-normalization entries are rerouted; fragment/tiled/batched-normalization variants retain their old dispatch. Weights and numerical accumulation order are unchanged.

Expansion: 16 waves each compute 32 rows × 32 hidden columns. Each B fragment serves two row tiles. Later contraction/projection/QKV: wave/8 selects the 16-row tile and wave%8 selects 16 output channels. The contraction's 128-channel group follows the column wave. Shared storage is doubled; the two row tiles have disjoint raw-normalization and inverse regions. All workgroup barriers are uniform.

Compile the generated benchmark.cpp with the normal HIP MinGW command. Upload it as `hip-backend/benchmark_c128_m32.exe`, generated kernel as `hip-backend/c128-fused-row-reuse.hip`; `build.ps1` copies the frozen post-head baseline modules and builds gfx1200 and gfx1201. The runner uses the gfx1201 module; no gfx1200 hardware is available here.

`run.ps1` validates 12 frames per static/moving sequence at 900/1080, then ABBA timing. `-TimingOnly -TimingFrames 1000` excludes the first 200 frames from long-run means. `-ExtraControls` covers 720, temporal history, float input and float feature streams. Every control compares each RGB frame by SHA-256; timings use ordinary, unprofiled execution, with fixed inputs and no adaptive reuse. Scripts refuse benchmarks while known games/Magpie run.

Evidence and decision: `Development/results/c128-fused-row-reuse-20260921/`.

`prepare-timing.py` reuses the validated pure-HIP harness and adds one-shot timing of the first mapped C128 fused dispatch: 2000 warmup calls, 10000 measured calls, then full raw FP32 output comparison. Compile its pure.cpp without -municode as `pure_c128_m32.exe`; `time-kernel.ps1` runs ABBA using the same executable/module, with `DLSS5_C128_M32_DISABLE=1` selecting the old kernel. Do not use this instrumented host for full-network timing. Re-run `prepare.py` to restore the ordinary host.

The generated module MUST prepend the production build's HIP_PREPACKED_WEIGHTS=1, HIP_ISA_HALF=1 and HIP_FFN_HOIST_RES=2. Initial direct compilation missed the packed-weight macro: 900/1080 controls passed, but 720's generic fallback misread weights. Old-host/new-module and disabled-candidate cross checks reproduced the mismatch; adding the macro fixed 720. This was an isolated experiment build error, not a shipped-game bug. The targeted C128 old/new assembly remained identical after this correction.
