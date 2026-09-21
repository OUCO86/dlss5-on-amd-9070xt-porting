# Step3 result: balanced M32×N32 reuse is promising in isolation

Following pure-HIP counters pointing to C128 memory-side backpressure, compared row/column tile shapes for C128 expansion only. Actual block9 weights512×128; synthetic E4M3 input26624rows (not captured activation or end-to-end frames). Original FP8 values, per-output K order, and activation retained across candidates. Both architectures compile; all13,631,488 output bytes match baseline, including after every timed batch.

Initial short warmup trial had substantial first-slot drift and inconsistent M32×N64 sign; retained initial.csv but did not use as claimed gain. Longer10000 warmup/20000 measured launches per slot, host wall+sync, candidate order1,2,2,1:

| Candidate | Reference→candidate | Savings |
|---|---|---:|
|M32×N64 first|43.009→42.551µs|1.06%|
|M32×N32 first|42.248→35.143µs|16.82%|
|M32×N32 repeat|41.399→33.441µs|19.22%|
|M32×N64 repeat|41.443→41.147µs|0.71%|

Static kernel evidence (counts per wave):
- M16×N64:1024 outputs,40 global64 loads,32WMMA,106VGPR.
- M32×N64:2048 outputs,48 global64 loads,64WMMA,108VGPR.
- M32×N32:1024 outputs,32 global64 loads,32WMMA,98VGPR.
-All compilerOccupancy12 and scratch0.

Balanced shape reduces total operand-load instructions/bytes per same output tile, unlike prior16-byte B loading that only combined the same byte volume. This is consistent with the memory-pressure hypothesis but not proof of a unique microarchitectural cause. Throughput is hot isolated execution; no input-pack or integration cost included, no new RGB/temporal assessment. The first and second batches have different absolute clocks/cache conditions; compare matched ABBA controls, not cross-run fastest numbers.

Decision: prioritize a matched fused C128 implementation next. This turn investigated all3 requested directions; only this third direction has substantial operator-level potential. Do not deploy this standalone kernel or promise17–19% network/game improvement. Fused32-row staging/normalization/workgroup layout may increase cost and must be measured separately.
