# C128+C256 fused FFN matrix-stage marginal probes

900P full-network main baseline includes the adopted RGB-head input sharing. Each independent diagnostic module executes one matrix stage twice for C128 and C256, discarding the first result. Initial accumulator is restored; normalization/activation run only once. Opaque asm input operands keep the first result live and memory clobbers inhibit load/CSE elimination. No device instruction is emitted for empty asm, but register scheduling/reload costs can change.

160-frame ABBA, discard32, frozen capture, temporal/reuse off, host wall. Every variant's final RGB equals baseline and all frame statistics finite. Measured marginal costs across BOTH channel families:
- Expansion matrix approximately0.5524ms.
- Contraction matrix approximately0.0975ms.
- Post-contraction projection approximately0.1351ms.
- QKV matrices approximately0.4162ms.

These are perturbation costs, not additive exact stage durations or achievable savings. They exclude extra copies of activation/normalization and do not isolateC128 vsC256. Diagnostic code changes resource allocation; do not infer that remaining family time is all barriers. gfx1201 compiled/run only because these are non-shipping probes, not candidate release modules.

Next experiment: C128 contraction output currently aliases expansion input and requires a barrier before overwrite. Separate2112-byte output storage removes that one barrier while retaining the post-write barrier and original arithmetic. Measure whether the extra LDS costs more than the synchronization saved. Matrix expansion/QKV are larger measured targets for subsequent arithmetic-preserving work.
