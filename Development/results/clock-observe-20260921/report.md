# Frequency/power clue follow-up — 2026-09-21

Forum report: increasing a power limit from~340W to350+W improved displayed gameFPS2–3. That is not itself a measured inference/core-frequency response: game rendering, clock changes and actual power differ from configured limits.

## Ordinary inference telemetry

Read-only ADL queries every200ms aligned by GetTickCount64 to current HIP replay frames.1000 frames each, discard first100 for warm analysis, adapter0/status0/supported counters only. No clock/power/voltage changes, no games running; model outputs retain90075aaba5e…/10801de20c21… hashes.

| Tier | Warm frame median | CoreMHz min/median/max | Memory clockMHz | BoardW min/median/max | Edge/hotspot median°C |
|---|---|---|---|---|---|
|900|13.2325ms|2774/2786/2807|2505|297/324/348|52/82|
|1080|18.704ms|2728/2739/2780|2505|318/325/362|55/85|

57/80 matched telemetry samples. Graphics activity median98%/99%, memory activity25%/27%: these activity sensors are not shader FLOP efficiency or bandwidth counters. ASIC/GFX power and throttle-reason/percentage sensors unsupported; cannot declare thermal- or power-limiting from this run. Board power supported; readings not equal to power-limit configuration. Memory clocks from different APIs may use different domains; do not compare ADL2505MHz directly with RGP's1259MHz metadata as a2x change.

Ordinary core median is6.2%/7.8% below advertised2970MHz boost. Scaling the earlier ideal matrix budget linearly by core frequency gives~2.13/3.10ms versus measured13.23/18.70ms, still about6.2x/6.0x. This remains a simplified principal-matrix budget, not achieved utilization. Frequency difference alone does not explain the earlier6x gap. No meaningful causal fit from the narrow natural frequency range or from comparing two different resolutions.

## RGP frequency context

Earlier capture logs explicitly say clocks set to peak then restored. Its SystemInfo records engineClockHz.max=2520000000; AsicInfo also contains2520000000 in the core-clock fields. This differs from ordinary run's2.74–2.79GHz. Treat prior memory-unit/cache percentages as the profiling interval, not as a measurement under identical ordinary-game clocks. rgp-gpu-metadata.json preserves the reported fields; no simultaneous ADL sampling existed during that earlier capture, so metadata is not a fresh measured frequency time series.

GPUCounterFreq is100MHz. A preliminary timestamp/byte-counter conversion on the old trace gives~30.794ms sampled span, but named Fetch/Write/Local-video byte counters have different scopes and must not be conflated with externalDRAM throughput. No new bandwidth saturation conclusion is made. Proper next step is per-kernel attribution and a controlled engine/memory frequency comparison under matched clocks; keep user's tuning unchanged unless conducting an explicitly scoped temporary profiling experiment.

Sources:
- Existing read-only ADL tool and AMD definitions: Development/HIP/adl-telemetry.md; https://github.com/GPUOpen-LibrariesAndSDKs/display-library/blob/master/include/adl_defines.h
- AMD clock-mode constraints: https://gpuopen.com/manuals/gpu_performance_api_manual/api_functions/gpa_opencontext/
- Official9070XT peak reference: https://www.amd.com/en/products/graphics/desktops/radeon/9000-series/amd-radeon-rx-9070xt.html
