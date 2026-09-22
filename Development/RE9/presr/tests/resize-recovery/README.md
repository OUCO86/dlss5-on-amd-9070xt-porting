# 0.28 resize recovery reproduction

2026-09-22, amd9070 RX9070XT, game/Magpie process guard passed. Loaded released ABI2 runtime SHA256 `f5cf76979d1753ce3e4498f85a45046b984ca8b0e54c80f17a41c45481e7cb68` directly from the real 0.28 staging package, using its HIP modules/model/shaders. No production binary or game files modified. Disk shader caching disabled in the test process only; network tier set to auto there.

`results.txt` contains four separate process runs. Each creates one runtime session; prime cases first call PrepareFrame with an actual 2560×1080 RGB9E5 texture, then retry with a valid texture in the same session. Fresh controls skip the invalid call. Exposure is null, so this specifically isolates geometry recovery rather than exposure behavior.

| Sequence | Valid PrepareFrame | Valid RecordInputs |
|---|---|---|
| fresh →1280×544 | OK | OK |
| fresh →960×544 | OK | OK |
| 2560×1080→1280×544 | OK | `bridge input capacity` |
| 2560×1080→960×544 | OK | `bridge input capacity` |

Both invalid primes fail with `codec unverified input format/geometry`. All device removed reasons remain S_OK. This confirms persistent partial-initialization state poisons smaller-tier recovery in 0.28. It does **not** reproduce the user's `codec pso E_FAIL`; that remains distinct.

The harness records commands but never submits producer or consumer lists; no frame inference or output-quality claim is made. HIP initialization/prewarm does execute. Runtime Destroy reports OK, but fresh controls leave bridge in InputRecorded, for which the runtime intentionally abandons resources; process exit performs cleanup. Do not interpret these tests as a clean-teardown check or reuse this record-only harness for a long-lived process.

Build on Linux using the existing pinned, ABI2-adapted host checkout:

```sh
x86_64-w64-mingw32-g++ -std=c++17 -O2 -static -municode -I /tmp/re9-upstream-bridge-review/OptiScaler-DLSSNR-PreSR-Multipass-main/OptiScaler/dlssnr/backend/lmxxf_runtime probe.cpp -o resize-recovery.exe -ld3d12 -ldxgi -ldxguid
```

Place only the test EXE at `D:\DLSSNR-Lab\re9-presr\resize-recovery.exe`; `run.ps1` discovers the complete 0.28 package without hardcoding its Chinese directory name. Entry point is wmain. The imported ABI header comes from the GPL upstream host, not a modified copy of the ABI.

After the poisoned-session cases completed, two more independent fresh processes reused the exact same runtime/assets and succeeded at both valid dimensions; see `fresh-after-failure.txt`. This demonstrates process restart recovery with disk caching disabled, not persistent-cache recovery.

## Fixed candidate: real submissions

`submit.cpp` and `run-submit.ps1` add actual producer → HIP → consumer submissions, fence completion, FP16 RGB readback and output checks. Use the same build command as above with `submit.cpp` in place of `probe.cpp`. This harness only modifies copied shaders under the isolated lab candidate directory; never point the mode-3 injection at a game or release directory. The run script restores the isolated shader set before every suite and requires the GPU/game guard to pass.

Modes: 0 fresh, 1 oversized→valid, 2 valid→oversized→valid (same session), 3 intentional PSO failure with valid 1920×1080 input→valid smaller tier (same session), 4 reject new oversized/valid requests while the original frame is still recorded but unsubmitted, then complete that original frame. Mode 3 changes the isolated encoder shader's t0 to t8, producing root-signature incompatibility (`codec pso`, E_INVALIDARG), then restores source before retry. This tests recovery, not the user's unknown E_FAIL cause.

`submit-results.txt` covers modes 0–3 at 1280×544 and 960×544; `live-frame-results.txt` covers mode 4. All 10 cases / 12 submitted frames passed, no device removal, all RGB values finite and nonzero. Each geometry's output hash is identical in fresh, recovered, and protected-live-frame runs:

- 1280×544 RGB-half hash: `da298784373eb633`.
- 960×544 RGB-half hash: `7b1ad9f8f2cfd4d4`.

Hashes above use the harness's FNV-style accumulation over RGB uint16 values (not a cryptographic checksum). Candidate runtime SHA256: `1b51069c38095988f17403366ac09c1c2e047b28423c7385e669023cf42fbacf`. Candidate host SHA256: `0ef102295a759b51c0c7cba6b8eedb455e9759f5a2b7f9b96309e030c6cd0035` (`host-build.txt`, incremental MSVC build completed with warnings). No candidate is installed into a game or copied over the published 0.28 package.
