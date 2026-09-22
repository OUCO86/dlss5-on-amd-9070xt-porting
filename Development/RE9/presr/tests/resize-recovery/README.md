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
