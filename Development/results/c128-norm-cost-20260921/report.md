# Normalization is measurable, but empty barriers are not the large missing cost

Actual first mapped C128,26624rows. One compiled diagnostic kernel, runtime repetition controls,1000warmup/6000measured launches, per-caseABBA. Every slot compares13631488 feature+normalized output bytes against the original (28slots, allzero differences); first/final full-network rawFP32 matches. Both gfx1200/gfx1201 compile; execution on gfx1201.

| Repeated work inside each Q/K normalization |2 executions vs1, added μs|4 executions vs1, added μs|
|---|---:|---:|
|RawLDS store + both barriers + read/square/sum/rsqrt/inverse store|3.2241|11.4817|
|Read/square/sum/rsqrt/inverse store only|2.5944|7.3072|
|Empty barrier pairs only|0.0558|0.1389|

Original-vs-diagnostic single execution90.365667→90.404917μs (+0.039250). ActualVGPR108/LDS10816/compilerOccupancy12/scratch0 are unchanged. Repeat loops and empty barrier pairs remain in emittedISA (12static barrier pairs including conditional paths). So this is not merely deleting code or comparing unrelated kernel layouts.

One extra normalization round costs roughly3–4μs here, and the read/arithmetic portion has a visible cost. The two-round arithmetic case spans a clock/performance transition; its localABBA is preserved, while the four-round case independently supports the effect. Do not subtract modes to derive exact component costs: scheduling and overlap differ. Do not multiply this hot-repeat marginal number into a promised game gain or call it the exact original phase duration.

Empty barriers synchronize waves that have already completed the real exchange; no new traffic or unequal arrival is introduced. Their tiny increment says little about actual data-dependency stalls at existing barriers. This favors avoiding unnecessary whole work over spending more LDS to remove barrier instructions, consistent with the previous rejected buffer/residency probes.

Follow-up exact candidate: skip mapped16-row tiles wholly outside the valid rectangle, explicitly write both zero output buffers. It avoids the complete bias-free FFN/QKV work on those tiles, not just normalization. Separate evidence under results/c128-empty-tile-20260921.
