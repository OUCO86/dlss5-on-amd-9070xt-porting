# Locate the larger performance gap — 2026-09-21

**Correction:** later output checks found the mixed D3D12/HIP RGP capture changes the result (final6a933465… versus normal75aaba5e…). Its counter numbers below are retained as historical data, NOT valid normal-inference bottleneck evidence. The ordinary unprofiled bridge/Graph/burst comparisons remain valid. Use ../kernel-bottleneck-20260921 for bit-exact pure-HIP isolated captures.

Rechecked current main network including RGB-head sharing, not the old24ms-era bridge result. Reuse/history off, same frozen capture/network instance. Full before/after restore input outside timing; privateHIP uploads once and excludes codec/sharedD3D resources from its loop. CPU Enqueue and completion wait recorded separately. Burst4/16 preserves stream order but amortizes per-frame host wait/submission boundaries. Graph0/1 separate runs, not a strict cross-Graph ABBA. Raw private/burst/full-after output comparisons all exact and finite; Graph stats3builds/1479replays confirm actual reuse of graphs.

|900P /1080P|Graph0|Graph1|
|---|---|---|
|Full before median|13.1555 /18.6500ms|13.0335 /18.7040ms|
|PrivateHIP median|12.8940 /18.3980ms|12.8690 /18.3215ms|
|Full after median|13.2670 /18.8320ms|13.1540 /18.7310ms|
|CPU enqueue median|0.4540 /0.4465ms|0.1420 /0.1430ms|
|Burst16 per-frame mean|12.7056 /18.1859ms|12.7386 /18.2052ms|

Interpretation: removing bridge/codec/resource path changes only a few tenths of a millisecond on this no-history sample. CPU submission is not a hidden multi-millisecond cost. Graph reduces CPU enqueue, not the total by anything resembling the theoretical6x gap. Queueing ahead lowers privateHIP about0.13–0.21ms; not a usable sixteen-frame game queue proposal. CPU work overlaps GPU work; wait time includes GPU execution/driver scheduling and is not a measured GPU-busy counter. Do not sum independent medians or call privateHIP timing pure instruction time. No new optimization adopted from these diagnostic differences.

## Hardware capture

RDP CLI successfully captured400 HIP dispatches from render-op3000. ApiInfo8 identifiesHIP; TraceConfig explicitly400 (unlike the first1-dispatch trial).17775 SPM samples, interval4096. Raw trace94,749,063bytes remains on Windows underhip-backend/pipeline-gap-rgp/hip.rgp, SHA inrgp-counters.json. The short80-frame capture exited during transfer and failed; increasing lifetime to2000frames let processing finish. Mixed D3D12 client later aborting does not invalidate the successful HIP file. Logs show clocks restored for both clients.

Observed provider-derived counters, aggregated by referenced denominator counts:
- Instruction cache hit99.954%.
- Scalar cache hit97.139%.
- L0 cache hit73.351%.
- L2 cache hit95.425%.
- LDS bank conflict0% in this sampled range.
- Memory unit busy90.812% of GPU-busy cycles.
- Memory unit stalled21.695%; write unit stalled3.100%.

Promising investigation direction: memory-side activity/stalls inside GPU work, with mostL2 requests hitting cache. This does NOT say external640GB/s DRAM is saturated, that21.7% is removable, or that memory is the sole bottleneck. Memory and arithmetic may overlap; SPM capture is a400-dispatch interval rather than a precisely bounded game frame and may see other GPU activity. No per-kernel attribution or absoluteDRAM throughput yet. The old effective55TFLOPS estimate is principal arithmetic per full wall time, not a hardwareALU-utilization metric.

Parser checks every derived ratio sample against its referenced raw-counter arrays (max errors saved); averages use ratios of sums. RDF container validated against official format, derived schema inferred/checked from this capture, not an official RGP CSV export. Next: correlate SQTT event/kernel timeline with counter peaks and inspect instruction timing on the dominant kernels before editing more source schedules.

Sources:
- RGP WindowsHIP support: https://gpuopen.com/learn/rgp_1_14/ and https://gpuopen.com/manuals/rgp_manual/
- CLI capture options: https://gpuopen.com/manuals/rdp_manual/radeon_developer_panel_cli/
- RDF3 container: https://github.com/GPUOpen-Drivers/libamdrdf/blob/main/docs/specification.md
