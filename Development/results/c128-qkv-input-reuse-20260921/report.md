# C128 QKV input reuse — 2026-09-21

Inspected C128 fused FFN/contraction/project/QKV. Tested retaining the same8 input fragments in registers across Q,K,V phases, avoiding repeated LDS loads. Changes only C128 non-BatchNorm branch; expansion, contraction, weights, arithmetic and normalization orders unchanged. This adds16 scalar-register values live across QKV normalization barriers; no assumed occupancy or speed benefit.

Both gfx1200/gfx1201 compile.900/1080 × frozen/horizontal1px motion ×12frames gives48 exact paired RGB hashes, all recorded outputs finite. Uses one1296×720 HDR capture with controlled transformation; no broad game/temporal validation claimed.

Full-network160-frame ABBA, first32 discarded, reuse/history disabled, baseline includes adopted post-head RGB feature reuse:
-900:13.17930078125→13.18182421875ms, +0.0025234375ms.
-1080:18.6745859375→18.67541015625ms, +0.00082421875ms.

Differences negligible, no benefit. Do not adopt. All8 timing CSVs retained. Diagnostic48-frame checks excluded from timing claims.

ELF function-byte inspection confirms actual compiler changes: C128 byte-input feature-byte unmapped function10044→9980bytes, mapped11756→11664bytes; byte sequences differ. Smaller code is not evidence of lower runtime and does not identify the hardware bottleneck. No second timing round justified by these results.

Production source, installed games and0.27 packages remain unchanged. Experiment code/results committed for avoiding repeated trials. This does not test C128 fragment-packed weights or changes to contraction-to-projection staging.
