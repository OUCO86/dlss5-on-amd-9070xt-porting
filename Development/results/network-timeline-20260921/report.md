# Where the current network spends time

The highest-priority single family is the high-resolution C32 outer path: about35% of reconstructed compute-region time. This result is based on the current main, not the older marginal-duplication table. No inference code, game DLL or package was changed.

## Region ledger

| Region family | Dispatches/frame |900P ms|1080P ms|1080P share|
|---|---:|---:|---:|---:|
|C32|11|4.405|6.444|35.5%|
|C64|18|1.615|2.363|13.0%|
|C128|26|1.541|2.214|12.2%|
|C256|34|1.670|2.254|12.4%|
|C512|92|1.760|2.179|12.0%|
|ViT|49|1.488|2.471|13.6%|
|transitions|4|0.084|0.206|1.1%|

These families are contiguous algorithm regions; their boundary pool/upsampling work is included. C32 includes input fusion, both half-resolution chains and post/RGB; its11dispatches include one upsampling kernel. C512 has92dispatches but is much cheaper than C32. Launch count alone is therefore not the priority measure; the outer path handles far more image positions.

| Measurement control |900P ms|1080P ms|
|---|---:|---:|
|Normal pure-HIP wall median|12.855|18.300|
|Sparse-marked wall median|12.886|18.282|
|Sparse GPU compute-span median|12.607|17.958|
|Sum of paired region estimates|12.562|18.131|
|Dense experiment: normal wall|12.811|18.229|
|Dense experiment: marked wall (rejected)|23.422|28.720|

Reconstruction differs from the independently measured compute span by -0.36%/0.96%. Region sums come from separate localABBA pairs; they are estimates, not timestamps all taken in one undisturbed frame. Normal wall time also includes host submission/synchronization and the final device output copy. Do not label wall-minus-sum as an exact copy/idle duration.

## Link to the arithmetic-ceiling experiment

| Family |900P approximate principalGFLOP|900P principal-work/region-time TFLOPS|1080P equivalent TFLOPS|
|---|---:|---:|---:|
|C32|205.2|46.6|45.8|
|C64|84.0|52.0|51.0|
|C128|106.5|69.1|69.0|
|C256|132.2|79.1|83.8|
|C512|100.5|57.1|58.1|
|ViT|85.8|57.6|57.6|

This is a coarse accounting cross-check using the previous documented principal-matrix model, adjusted for the C128/C256 zero guards. It is not a complete dynamic instruction count: it excludes conversion/activation/normalization and simulated diagonal/reduction operations, and its transition accounting does not exactly match the timing-region boundaries. Precisions are mixed. Therefore these ratios are not ALU utilization and cannot be directly subtracted from the405TFLOPS register-only peak to claim removable waste. Nevertheless, high-resolution C32 combines the largest elapsed cost with the lowest principal-matrix work per total region time; it is the first target to dissect.

## What the real C32 machine code says

The assembly artifact was accepted only after its sibling binary SHA256 matched the timed module: `C381FCE5BB69927D8A33EBDD1ED2B083E4621BF504095CA3202E081034DFD67D`. The three representative kernels already contain substantial VOPD arithmetic; there is no evidence of a global missing-dual-issue switch.

| C32 kernel |WMMA static ops|single F32 arithmetic ops|F32 arithmetic ops in VOPD|conversion ops|LDS ops|
|---|---:|---:|---:|---:|---:|
|c32_fast_ffn_attention_fused_half_prefix_finish_main8|74|483|233|538|437|
|c32_fast_ffn_attention_fused_half_chain|70|447|243|412|387|
|c32_post_merge_head_half|58|530|338|434|417|

These are static code counts across control paths, not executed operation counts, eligible-pair percentages or time shares. Matrix instructions have different work/cost from scalar/vector conversions and memory operations. They identify format conversion/packing and shared-data exchange as questions to measure, not proven bottleneck fractions. The FP32 microbenchmark's26→50TFLOPS result cannot simply be applied to these kernels.

## Measurement failures retained and corrected

1. Begin/end events around all234dispatches preserved output and produced ordered timestamps, but added about10ms/frame. The resulting per-kernel cost table is rejected; timeline.csv is used only for dispatch topology and argument metadata.
2. An initial sparse implementation reused event handles and measured empty/very short intervals. It occasionally returned a negative interval (recorded example: cut0 prefix−0.016980ms). Those runs are rejected, not clamped or mixed into the final estimates.
3. Final sparse instrumentation uses a unique event triplet per frame, common endpoint handles for cut0/234, an end marker after the last compute kernel rather than after D2D copy, and explicit event readiness. Every region is a left/right cumulative-prefix difference,8ABBA pairs. All final event intervals are nonnegative and additive within the guard tolerance.17raw FP32 checks per tier (34total) match; existing900/1080RGB goldens also match. The driver-level cause of the earlier short-interval failure was not established.

The final480sampled frames/tier use only2–3markers each, with before/after unmarked runs. Tiny transition regions have some negative **paired differences** due to cross-frame jitter, while their event intervals are valid; preserve those samples and do not rank these tiny costs precisely. Region spans include queue/data movement within them; this is not proof that every nanosecond is arithmetic.

## Next bounded experiments

First, instrument C32's shared body with output-preserving repeated phases: FFN matrix work, activation/format packing, attention probability/normalization, and final projection. Compare repetitions1/2/4 in the same compiled diagnostic kernel; check output and emitted work, and measure instrumentation overhead/resources before trusting differences. This is preferable to another blind occupancy increase, a global FMA/fast-math change, or re-running the already-small procedural-noise hypothesis.

Second, use actual ViT FFN dimensions/data for a GEMM→activation/pack→full-operator comparison, to connect the register-only ceiling to a realistic workload. Do not change precision or reduction order to manufacture an apparent gain. These phase-specific experiments are next steps, not results already claimed here.

Evidence: final prefix.csv and prefix-baseline.csv, rejected dense timeline/frames data, exact-output logs, input/output/module hashes, summary.json, c32-isa.json and rejected-prefix/. Sources/tools: Development/HIP/experiments/network-timeline. Frozen real capture, Graph/adaptive/history off, current gfx1201 kernels. Results are inference-only, not a game-FPS claim.
