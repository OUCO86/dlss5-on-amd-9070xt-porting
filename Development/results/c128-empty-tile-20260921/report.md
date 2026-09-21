# Adopted: skip C128 all-zero vertical padding tiles

The main source adopts the small vertical-only guard from vertical.patch. A whole16-row mapped tile above/below the valid input rows writes canonical zeros to the entire feature and normalized-QKV output regions, then returns uniformly before LDS/barriers. Valid pixels retain the original computation. Later attention is unchanged. This is exact for the fixed finite, bias-free model and its canonical-zero FP8 conversion; it is not an approximate activation threshold or temporal reuse.

## Measurement

| Variant | Isolated mapped kernel μs | Gain |900P full-network savings|1080P savings|
|---|---:|---:|---:|---:|
|General rectangle intersection|91.50545→87.31165|4.58%|0.021789ms|0.025609ms|
|Vertical-only guard (adopted)|90.59945→85.54830|5.58%|0.043029ms|0.026763ms|

Each isolated result is its own ABBA,2000warmup/10000measured launches, real first mapped C128 input, ordinary pureHIP wall/sync. Whole-network general variant uses160frames/slot, discard32; adopted variant uses1000frames/slot, discard200. Full-network adopted baselines13.308934/18.779290ms, candidates13.265904/18.752527ms. ABBA endpoints drift; tiny gains are not a fixed FPS promise or a rigorous cross-run ranking. The simpler guard avoids extra divide/wrap calculations and has a clear isolated effect, with positive controlled full-network results.

Each variant passes96 paired RGB frames:900/1080 static and motion,720 motion,900 temporal history, f32input and f32feature controls. Each also passes8 raw FP32 network comparisons after repeated-kernel timing. No image-quality switches changed. Predicate checks cover1012geometries/72276tiles with zero false skips, including raster row wrap and very narrow geometries; the vertical guard conservatively permits partial tiles to run normally.

The representative900 mapped case is208×128 with valid200×120 shifted by4:104 of1664 workgroups lie entirely in top/bottom padding (6.25%). This is specific to that shifted stage, not the fraction of the entire model removed. Other mapped shifts may have no complete zero vertical tiles.

Both gfx1200/gfx1201 compile, execution is gfx1201 only. Adopted mapped byte-input kernel actualVGPR109 versus108, LDS10816/compilerOccupancy12/scratch0 unchanged. Candidate module built with the production defines; after applying the patch, the full production source matches the validated generated source exactly after stripping its three build defines. No DLL ABI/configuration changes. Game installations and0.27 archives were not replaced.

## Reproduction and continuation

Sources/scripts: Development/HIP/experiments/c128-empty-tile (base79c1654). Both variants' summaries, per-frameCSV, flags, output hashes and artifact hashes are archived here. Current production is the adopted vertical version; use pinned generators to reproduce its comparison against the pre-change post-head baseline. The general predicate is research only.

The preceding normalization-cost probe is under results/c128-norm-cost-20260921: repeated whole exchanges add~3–4μs per extra round, while empty synchronized barriers add little. That result motivated avoiding complete unnecessary work rather than spending more LDS to remove barrier instructions. Next candidate: independently assess similar exact zero-padding guards for C64/C256; do not assume their padding fractions/resource tradeoffs are the same or deploy them without controls.
