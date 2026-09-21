# C128 contraction output buffer — 2026-09-21

Follow-up to stage-cost diagnostics. The original contraction writes its output over shared expansion input, requiring all waves to finish reading first. A dedicated2112-byte C128 output buffer removes that pre-write barrier; the post-write barrier and projection arithmetic remain unchanged. C64/C256 take original paths. This tests synchronization savings against increased LDS allocation, not sparsity or precision changes.

Both gfx1200/gfx1201 compile.900/1080 static/1px horizontal motion,12frames each:48 paired RGB hashes identical, all frame stats finite. One captured image and controlled transform; not a new game/temporal validation.

Clean160-frame ABBA, discard32, host wall, no RGB diagnostic writes, history/reuse off:
-900 baseline13.232933594ms→candidate13.240246094ms, +0.0073125ms.
-1080 baseline18.694265625ms→candidate18.72125ms, +0.026984375ms.

No demonstrated gain, do not adopt. Full8 timing CSVs retained. Extra LDS/changed scheduling are plausible tradeoffs, not a measured occupancy diagnosis. Production, installed games and0.27 packages unchanged. Stage-cost data instead points toward expansion/QKV matrix work as larger measured regions; those figures remain non-additive perturbation costs.
