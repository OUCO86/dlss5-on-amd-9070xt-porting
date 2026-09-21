# RX9070XT arithmetic throughput probe

A standalone register-resident compute ceiling test, not GEMM/network throughput. Runtime-loaded nonzero operands stay in registers during the loop; independent accumulators have distinct initial values. Every accumulator component feeds a final per-thread checksum, all returned checksums are checked exactly. Inputs are1/16, represented as E4M3 byte0x18, binary16 word0x2c00, or float32. Binary-fraction increments remain exactly representable for all tested loop lengths. The short3-iteration and sustained workloads are both checked.

Kernels use256threads/wave32. Sweep independent accumulators1/2/4/8/16 and64/256/1024workgroups. Each outer iteration unrolls16operations per accumulator; iterations2048 for matrices and8192 forFP32. Each16×16×16 dense WMMA issues8192FLOPs **per wave**, not per thread. A scalarFMA counts2FLOPs; a dualFMA instruction contains two such operations. No sparse instruction is used. Counting formulas:

* Matrix: groups ×8waves ×accumulators ×16 ×iterations ×8192.
* FP32: groups ×256threads ×accumulators ×16 ×iterations ×2.

The checksum, loop control, initial loads and final store are excluded from the operation numerator but included in time, so their overhead lowers achieved throughput. An emitted-ISA audit confirms all selected configurations' unrolled operation counts, including128WMMA per iteration for matrix8 and256FP32FMA operations per iteration for vector16. No scratch spills in those selected kernels.

The plain fp32 variant shares an operand pair among accumulators; its compiled loop uses single v_fmac_f32_e32. fp32d loads two independent operand pairs and alternates them, allowing register-bank-compatible VOPD:128dual instructions perform256FMAs. This is the benchmark's FP32 peak case. Both use identical known numeric operands/results, but the compiler cannot treat the separate runtime loads as identical. Do not transplant this loop into model code or change its rounding order on the strength of this benchmark alone.

Build bench.cpp using MinGW `-std=c++17 -O2 -static`. It dynamically loads the existing HIP7 runtime and module. `run.ps1` assumes the existing9070Windows lab at D:/DLSSNR-Lab/hip-backend/gpu-throughput, compiles both gfx1200/gfx1201 with rtc_compile.exe, then executes gfx1201 while guarding known games. The standalone executable takes `MODULE.hsaco [KIND [ACC GROUPS]]`; it always reports its actualdevice0 name/architecture. A different target needs its matching module. Runtime validation here is gfx1201 only.

Default sweep uses five batches targeting150ms each, calibrated from a pilot, plus warmup; reported configuration rates are medians, not best single samples. Host wall/synchronization time is primary; HIP events provide a cross-check. Batch duration and sample count are bounded optional environment settings GPU_THROUGHPUT_BATCH_MS / GPU_THROUGHPUT_SAMPLES. `repeat-best.ps1` repeats fp8_8/fp16_8/fp32d_16 with256groups, nine batches targeting300ms. Calibration includes initial-clock effects, so actual durations are in CSV.

The read-only clock_observe_telemetry.exe helper is documented in ../clock-observe/README.md and ../../adl-telemetry.md; it samples ADL every200ms. Scripts query clocks/temperature/power but do not set clocks, power, voltage or fan limits. analyze.py uses adapter0/status0/supported sensors within each timed configuration's GetTickCount64 interval; these coarse samples are observations, not a controlled frequency sweep.

Results: Development/results/gpu-throughput-20260921. The archived initial run swept45configurations before adding fp32d; dual/ has12extra configurations, and repeat-* holds three independent nine-batch repetitions. The current executable's default sweep includes all57configurations. All60measured configurations (including repeats) passed checksums. No game or inference code changed.
