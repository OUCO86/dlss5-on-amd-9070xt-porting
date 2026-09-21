# C256 expansion paired-K weight layout — 2026-09-21

Implements the proposed16-byte load experiment. CPU-only initialization permutes expansion-weight fragments; GPU uses one128-bit B load per pair of original K16 MMAs. Same bytes, no quantization/pruning, same per-accumulator K order. Only C256 expansion weights change, and A remains two64-bit fragments. This is a matched experimental host/kernel pair, not a drop-in module for existing game DLLs.

Both gfx1200/gfx1201 compile. Real mapped C256 bytein_fb ISA: global_load_b64152→88, global_load_b1280→32, WMMA136→136; static opcodes2122→2030. next_free_vgpr101→97 but VGPRBlocks12/Occupancy12 remain equal; LDS21568/private0 unchanged. No claim of doubled total bandwidth or measured occupancy increase.

900/1080 frozen and horizontal1px motion,12frames each,48 paired RGB frames all bit-identical and finite. These are controlled transformations of one capture, not general game/temporal/720 coverage. Timed runs check first/last outputs; not every intermediate timed frame is read back.

| Comparison |900P baseline→candidate|1080P baseline→candidate|
|---|---|---|
|160frames, discard32|13.170578→13.165664ms|18.653461→18.623523ms|
|1000frames, discard200|13.300928→13.302034ms|18.837969→18.809923ms|

1080 saving about0.030/0.028ms (~0.15%);900 initial0.005ms disappears to~0.001ms regression in long test, effectively tied. Endpoints drift, so this is modest repeat-observed candidate benefit, not a formal confidence interval or gameFPS prediction. All16 timing CSVs retained. No claim that wider loads explain or fix the large theoretical-throughput gap; total bytes and matrix math are unchanged and substantial remaining operations persist.

Decision: retain experimental implementation. Production source, installed games and0.27 ZIPs unchanged. Full adoption would need distinct wide-layout entry names/host routing (current trial reuses symbol names and would silently mismatch an old host), wider controls and release rebuild. Potential next experiment can extend paired B layout to other matrix regions independently; no such extension was done here.
