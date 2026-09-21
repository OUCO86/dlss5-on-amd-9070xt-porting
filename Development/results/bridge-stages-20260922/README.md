# Independent staged bridge implementation

Design credit: [TheAutomatic](https://github.com/TheAutomatic), whose [PR #5](https://github.com/lmxxf/dlss5-on-amd-9070xt-porting/pull/5) proposed composable D3D12/HIP stages, optional fast-prefix noise and per-frame codec parameters. User requested an independent implementation rather than merging that PR. Pre-change reference: 613c278c0281b4ee0b2ea5b6cc3f3b3315b9e3ae.

## Implemented

- RecordInputCopy / EnqueueAfterProducer / RecordOutputReadable, plus explicit NotifyOutputSubmitted acknowledgement. Phase checks, real queue/device/list identity checks, history consistency, failure poisoning, safe retirement and source-reference lifetime preservation. Existing Run reuses the internal stages; its Graph and diagnostic behavior remains available. Staged Graph is rejected before recording.
- Typed LUID selection accepts an exact match despite spoofed DXGI vendor identity. Architecture validation, gfx1200/gfx1201 path routing and diagnostic fields retained; unique AMD/no-LUID name fallback only, no blind count==1 fallback.
- fast_prefix accepts empty noise while retaining synchronization/Graph reset semantics. Normal and RE9 initialization skip the unused 192MiB CPU table after loading flags. Non-fast/HLSL paths retain the table requirement.
- Explicit NativeCodecParameters for per-dispatch strengths and debug view; legacy DLSS5_STRENGTH remains the default for old callers. Finite/range validation, shader compiler error text and existing codec-step diagnostics retained. Independent codec test root constants expanded to 20 words to initialize the debug field.

## Evidence

Actual GPU: RX9070XT gfx1201, HIP runtime70260201. No game installed or launched.

- 31 raw FP32 comparisons: 900/1080 old Run versus staged calls, with/without history, multiple seeds. Three distinct-seed frames queued before waiting, each readback checked; seed references are asserted different to detect stale frames. Legacy Graph build/replay also matches.
- 133 invalid/error calls rejected: ordering, wrong producer/consumer queue on the same device, mismatched history flag, missing acknowledgement, staged Graph, injected HIP launch failure and subsequent poisoned reuse. Retirement tested false before stage completion and true after acknowledged work. Failure injection changes only the test instance's launch pointer; it does not remove the GPU device.
- Root/architecture and flat module paths verified in real Create; empty noise vector used throughout. Fake NVAPI and physical multi-GPU hosts were not actually injected/tested.
- 24 old/new codec byte comparisons: full1080 FP16, FIT FP16, FIT UNORM8/sRGB, nondefault legacy strengths, explicit strengths, paper-white1/0.5/2 and restoration after per-call overrides. 12 debug-view changes verified; FP16 debug outputs finite. Invalid parameters rejected.
- Existing independent codec harness: 3 old/new decode comparisons at256×256, each262144half values, different=0/invalid=0.
- 44 production shader variants compiled, including raw R11 output binding validation.
- HIP addon, RE9 post-present addon and HLSL compatibility addon compiled. Local binary hashes/sizes in build-artifacts.json; test/shader hashes in artifacts.json.

Logs are normalized to UTF-8/LF; summary.json records counts. API usage and lifetime contract: ../../HIP/staged-bridge.md. Tests: ../../HIP/tests/bridge-stages.

## Scope

This delivers integration building blocks and preserves existing paths. It does not automatically identify a safe mid-frame boundary in RE9, switch its post-present processing to pre-upscale, remove its resolution limit or prove fullscreen compatibility. Those require a separate host integration/game test. No PR was merged and no comment was posted on the contributor's behalf.
