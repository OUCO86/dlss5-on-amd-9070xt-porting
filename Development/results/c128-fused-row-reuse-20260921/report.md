# C128 balanced row reuse: full fused kernel

Experimental specialization of the main branch's exact FFN/QKV, no model/weight/precision changes. Expansion uses M32×N32 per wave; the remaining phases use two 16-row groups of eight column waves. Thread count 256→512 and workgroup row count16→32. Only compatible C128 row-major entries are routed; production source/game packages are unchanged.

## Validation and construction correction

Both gfx1200/gfx1201 compile. Runtime tests use gfx1201 only. Ordinary controls compare every captured RGB byte by SHA-256 (see hashes.json and summary.json). The pure-HIP repeated-kernel control compares raw network FP32 results against the previously captured reference at post_shift=3, both first and final frames.

The first direct module compile omitted HIP_PREPACKED_WEIGHTS=1. 900/1080 passed, but 720 differed. Old host + new module, and new host with the M32 path disabled, both reproduced the 720 mismatch: it was not introduced by the new work partition. The generic fallback read packed weights as floats. The generator now prepends the same three definitions as hip/build-modules.ps1. The targeted old/new C128 annotated assembly is unchanged after correcting that macro. Initial evidence remains in initial-build-audit.json; final 720 checks use the corrected build. No released DLL/module was replaced.

## Resources and what the change actually saves

| Mapped C128 byte-in/byte-feature kernel | Old | M32 |
|---|---:|---:|
| Static global_load_b64 | 80 | 72 |
| Static FP8 WMMA | 72 | 72 |
| Actual VGPR | 108 | 103 |
| LDS bytes/group | 10816 | 21632 |
| Compiler occupancy | 12 | 12 |
| Scratch bytes | 0 | 0 |
| Barrier signal/wait pairs | 8 | 8 |

The workgroup covers twice the rows, so LDS bytes **per row** are unchanged. Doubling LDS alone does not establish a regression or explain the whole result. Static counts are not dynamic bandwidth/time fractions. Compared with the earlier standalone expansion, the whole kernel retains the contraction, residual/projection, QKV and normalization work. Its load reduction is only 8/80 static 64-bit instructions, rather than 8/40 for standalone expansion. Arithmetic, conversion and synchronization remain.

## Timing and decision

See summary.json for ordinary end-to-end ABBA (1000 frames/slot, discard first200) and kernel-*.log for isolated repeated-kernel ABBA (2000 warmups,10000 measured calls). Isolated timing is hot-cache host wall/sync without RGP, not a game frame attribution. Full-network tests freeze inputs, disable adaptive reuse, and do not claim a game FPS increase.

Final corrected build: **96 paired RGB frames match byte-for-byte**; eight raw FP32 network comparisons after repeated-kernel runs have zero differences.

| Ordinary full-network replay | Baseline ms | Candidate ms | Saved ms |
|---|---:|---:|---:|
| 900P | 13.318090 | 13.288563 | 0.029527 |
| 1080P | 18.798874 | 18.745182 | 0.053692 |

Isolated mapped C128 fused kernel: 90.752850 → 88.250450 μs, **2.76%** improvement. ABBA slot values are in summary.json; initial pre-correction run was also ~2.7%. Macro correction left these targeted kernels' assembly unchanged.

Keep this as a small-gain experimental candidate. The standalone17–19% does not survive as a comparable full-fused/full-network gain. Next bounded hypothesis: extend row-wise B-fragment sharing through contraction/projection/QKV, keeping per-output K order. This will require balancing accumulator count and workgroup geometry across all phases; do not simply widen the expansion again or infer that a larger tile must win.
