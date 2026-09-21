# RX9070XT reaches its arithmetic roof under a register-resident workload

The standalone program is written and executed on the actual RX9070XT/gfx1201 with the existing WindowsHIP7 runtime. Dense FP8, FP16 matrix and properly dual-issued FP32 all reach approximately the advertised capacities. No inference/game code or clock/power configuration was changed.

## Independent repeat of the selected configurations

Nine measured batches per row after a pilot/warmup; rates below are medians of **host wall/synchronized** throughput, not the fastest event sample. Each row uses256workgroups/256threads;8independent accumulators for matrices,16 forFP32.

|Arithmetic|AMD nominal TFLOPS|Measured TFLOPS|Observed core clock median|Reference at observed clock|Measured/reference|
|---|---:|---:|---:|---:|---:|
|Dense FP8 WMMA, FP32 accumulate|389|405.280|3114MHz|408.158TFLOPS|99.3%|
|Dense FP16 WMMA, FP32 accumulate|195|204.301|3173MHz|207.946TFLOPS|98.2%|
|FP32 vector, dualFMA|48.7|49.921|3161MHz|51.790TFLOPS|96.4%|

Nominal values and the2970MHz reference boost come from [AMD's RX9070XT specifications](https://www.amd.com/en/products/graphics/desktops/radeon/9000-series/amd-radeon-rx-9070xt.html). Clock-adjusted references use64CU × observed coreMHz × FLOPs/clock/CU:2048 forFP8,1024 forFP16 matrices,256 for dual-issuedFP32. AMD's matrix rates are documented in [GPUOpen](https://gpuopen.com/learn/accelerating_generative_ai_on_amd_radeon_gpus/#dense-wmma-rates). These are approximate references from coarse ADL clock samples, not cycle-accurate utilization counters. The card's observed clocks exceed the reference boost, explaining throughput modestly above nominal.

Repeat ranges: FP8 404.749–408.678TFLOPS; FP16 201.869–205.935; FP32dual49.841–50.027. ADL core samples span3110–3137,3136–3183 and3152–3165MHz respectively. Board-power medians330/276.5/296W are read-only observations under the machine's existing configuration, not a test locked to reference-board power. Memory-clock reports were much lower than in network inference, consistent with negligible DRAM traffic here; they are not a controlled memory-frequency experiment.

## The FP32 measurement trap and correction

The initial ordinary FMA loop achieved only~25.9TFLOPS. ISA confirms256 single v_fmac_f32_e32 instructions per unrolled loop. Reusing the same operand registers did not form dual issue in this compiler. Loading separate runtime operand pairs and alternating them gives128 VOPD instructions, each containing two v_dual_fmac_f32 operations: still256FMAs, now two per issue. The first dual sweep reached49.707TFLOPS and the independent repeat49.921. Register-bank-compatible operand scheduling matters; source-level independence alone did not suffice. VOPD pairing syntax/constraints are described by [LLVM](https://llvm.org/docs/AMDGPUInstructionSyntax.html#syntax-of-vopd-instructions).

This is a new optimization lead for examining scalar portions of real kernels, not proof that inference can double: WMMA already uses different execution hardware, many scalar operations are dependent, and the model's rounding boundaries must be preserved.

## Method and checks

Operands are loaded once into registers and reused. This intentionally removes main-loop global/LDS traffic, normalization, activation, and inter-kernel exchanges. All operands are nonzero and instructions dense;389TFLOPS is the comparable FP8 nominal, not779sparseTFLOPS. Each WMMA16×16×16 counts2×16×16×16=8192FLOPs per wave. FP32 counts2 per FMA. Formulas, code and exact-checksum design are in experiments/gpu-throughput/README.md.

Initial sweep45configurations + dual sweep12 +3selected repeats =60validated configurations,312timing batches. Runtime-loaded data, distinct accumulator seeds and consumed full-fragment checksums keep computations live. Short and sustained loop outputs match exact binary-fraction expectations. ISA auditing confirms selected loop operation counts and zero scratch spills. Bothgfx1200/gfx1201 compile; onlygfx1201 was executed. HIP events and host wall time agree closely; initial sweep event times are0.9928–0.9996 of wall times. RawCSV retains both, and summary.json rechecks the operation counts/rate calculations independently.

The runtime reports32multiprocessors and wave32; do not mistake that runtime unit for the advertised64CU count. Actual FLOP accounting uses launched waves/threads and instruction shapes, not that property. Per-case clock/power samples are matched by shared Windows uptime timestamps, adapter0/status0/supported fields only. Data, module/runtime hashes and versions are archived here.

## Meaning for this project

The GPU is demonstrably capable of roughly400TFLOPS of dense FP8 under a suitable workload. The network's earlier~55TFLOPS estimate counts principal matrix work over mixed-pipeline time; it is not the physical card's compute ceiling. This test does not establish an achievable400TFLOPS GEMM or a7× network speedup: real work still includes loading/packing operands, limited reuse, dependencies, padding, conversion, synchronization and other arithmetic. A next useful bridge is a representative GEMM/input-shape benchmark between this register-only ceiling and the complete fused operator.
