# C32 mapped-half input single FP8 packing

One reversible, lossless candidate on main0.27 baseline. RawMapped C32 prefetch input currently computes F(half_input), then fp8() for LDS. Candidate packs once and explicitly canonicalizes input signedzero to preserve F semantics. Residual reads and Merge/non-RawMapped paths remain unchanged. This revisits the older single-cast idea at the current prefetch staging site, not a claim that the idea itself is new.

Both gfx1200/gfx1201 modules compile. Direct GPU enumeration of65536 half encodings (including zeros/subnormals/nonfinite) yields zero packed-byte mismatches.900/1080 × static/1px horizontal motion ×12frames =48 paired RGB frame hashes match; all replay outputs finite. Diagnostic runs save/read frames and are excluded from timing claims.

Clean160-frame ABBA, first32 discarded, ViT reuse/history off, frozen input, host wall time:
-900 baseline13.213125ms, candidate13.213789ms, +0.000664ms.
-1080 baseline18.706363ms, candidate18.702547ms, −0.003816ms.

No demonstrated gain. Do not apply candidate.patch to production or deploy modules. All8 timing CSVs retained; original remote per-frame RGBs under hip-backend/c32-single-pack-results. Tools experiments/c32-single-pack/prepare.py, build.ps1, check.cpp, run.ps1. Kernel source unchanged on main, games/packages unchanged. Next work should examine a larger memory/synchronization cost rather than further tiny conversion-only variants.
