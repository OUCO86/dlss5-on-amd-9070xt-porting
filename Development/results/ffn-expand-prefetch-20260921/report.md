# FFN expand batched weight loads — 2026-09-21

Based on expansion's larger marginal cost, moved four same-K weight fragment loads ahead of the four independent MMAs for C128/C256. Per-accumulator K order unchanged. No new precision/weight/cache policy. Both architectures compile.

ELF function-body comparison on gfx1201:
- C128 unmapped bytein_fb10044→9972bytes, differs.
- C128 mapped bytein_fb11756bytes, identical.
- C256 fragment unmapped12572bytes and mapped14472bytes, both identical.

For those three identical functions, the source rewrite produces no instruction change; do not claim new prefetch overlap. This differs from the older09-19 C256 tiled-layout next-iteration experiment, which was also negative and did not form useful overlap.

900/1080 frozen/1px horizontal motion ×12 =48 paired RGB frames identical, all frame stats finite. Clean160-frame ABBA, first32 excluded, temporal/reuse off, host wall:
-90013.206886719→13.218671875ms, +0.011785156ms.
-108018.688054688→18.691726563ms, +0.003671875ms.

No gain; reject. Values are near drift/noise and do not establish a universal slowdown. All8 timing CSVs and code-comparison.json retained. Production, installed games and0.27 ZIPs remain unchanged. Next scheduling probes should inspect active machine-code changes first, rather than assume source reordering creates new hardware overlap.
