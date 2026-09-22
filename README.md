# DLSS 5 (DLSSNR) on AMD RX 9070 XT

[中文说明](README.zh-CN.md)

A from-scratch Direct3D 12 re-implementation of NVIDIA's DLSS 5 neural renderer ("DLSSNR", the 71-block
Swin/ViT network shipped in `nvngx_dlssnr.dll`) that runs on an AMD RDNA 4 GPU. The network was reverse-engineered
block by block, re-written as HLSL compute shaders using Shader Model 6.10 wave-matrix (`dx::linalg`) intrinsics with
FP8 (E4M3) operands, and wired into a game through a ReShade add-on that hooks the FSR dispatch and post-processes the
1080p frame.

**REFramework variant (0.28)**: special RE9 integration using a matched modified OptiScaler host and `LmxxfNrRuntime.dll`: rendering → HIP DLSS5 → FSR → display. Tested2560×1440 borderless output; same-frame exposure normalization/restoration fixes the omitted exposure. Neural input remains≤1920×1080 with automatic network tier selection. F6 is handled by the new host; the old post-present addon is disabled. Other RE games, including Xbox Onimusha previously tested with the old route, require new validation.

**Latest (2026-09-22, 0.28)**: six shared lossless kernel improvements—RGB head read sharing, exact-zero C128/C256 padding shortcuts, and fixed-shape ViT expansion/projection plus decoder projection. Stellar Blade gameplay showed no visible regression or FPS change; no fixed speedup is promised. Regular packages retain their existing hosts; RE9 uses the new pre-SR host and exposure fix. No new lossy optimization. Full models and gfx1200/gfx1201 kernels are included; optional adaptive reuse remains off by default in regular packages.

**Release configuration**: package defaults are tracked in [scripts/CONFIGURATION.md](scripts/CONFIGURATION.md); fresh packages copy the matching repository template instead of inheriting local gameplay settings.

**Regular add-on features retained from0.27**: exact streaming ViT attention is enabled in source builds. Optional R3 adaptive reuse is disabled by default; enabling it trades some accuracy for speed. See [configuration and matched DLL/module requirements](Development/HIP/VIT-REUSE.md). INT4 and sparse pruning experiments are not included. The0.28 RE9 runtime does not use this addon configuration/hotkey path.

**Status (2026-09-17, `0.20`, HIP backend)**: the inference backend moved from DirectX 12 Shader Model 6.10 wave matrix to AMD HIP — the 24 network kernels ship as gfx1201 binaries (`.hsaco`) and run through the HIP 7 runtime that comes with the AMD driver (`amdhip64_7.dll`). Output is bit-identical to the 0.15 DX12 chain (same 40-frame output hash); isolated 1600×900 inference 16.8 → ≈15.5 ms, Stellar Blade in-game 900p 47 → 52 fps. No Agility SDK 1.721 preview runtime, no Shader Model 6.10 and no Windows Developer Mode are needed any more. The DX12 chain below stays as documented history.

**Status (2026-09-13, Magpie bundle `0.15`)**: ordinary game windows up to **1920 pixels wide and 1080 pixels high** now work on RX 9070 XT. Smaller or slightly cropped windows are fitted automatically, preserving their aspect ratio. FSR4 then scales the processed picture to the screen; XeSS Frame Generation (ZeroMV) remains enabled. Games do not need native FSR/DLSS support.

In the user's *Onimusha* test, a 1080p window scaled to 2K maintained about **30 fps**. A separate synthetic-window test on a 4K desktop measured about **29 network fps**; these are different scenarios, not a before/after frame-generation comparison.

**The `FSR3_SR` item in the effect group is the DLSS5 entry point.** The add-on runs DLSS5 through that item while its UI name remains FSR3; there is no separate DLSS5 filter to add. Keep this first item at input size; the following FSR4 item handles upscaling. Enable AMDOF only for the first item; set Optical Flow Method to None for FSR4 and XeSS Frame Generation, which looked sharper in the user’s test.

The portable preset runs **FSR3 (DLSS5 through this add-on) → FSR4 filling the screen → XeSS Frame Generation**. Small-window adaptation (`DLSS5_FIT_INPUT=1`) and the network FPS display are enabled; the FPS number refreshes at intervals of at least three seconds.

0.20 (HIP) needs a driver that ships `amdhip64_7.dll` (verified by us on AMD 32.0.31007.2048, the same preview driver as before; a user reported on 2026-09-17 that the release driver, which ships the same file, works too). The DX12 editions up to 0.15 need Windows Developer Mode and AMD's 26.10.07.02 preview driver. The HIP add-on takes 1.2 GB of VRAM at 900p (0.6 GB weights, 0.3 GB activations, 0.07 GB shared buffers, plus runtime overhead; `DLSS5_HIP_MEMORY=1` writes the breakdown to `logs\native-hip.txt`). VRAM pressure still drops the frame rate and does not recover; for the Stellar Blade in-game hook, use texture quality "High" or lower. Since 0.22 the 900 tier pads 1600×900 to 960 rows instead of 1024 (60 reflected rows plus one row of zero ViT tokens, the way the 1080 tier pads its token grid): same kernels, ≈6% less work (15.2 → 14.4 ms), output differs from the 0.21 layout (31.5 dB) with no reference to call either one right; the 0.21 layout stays available as `DLSS5_NETWORK_HEIGHT=900w` and remains the bench geometry of the bit-exact goldens (`Development/HIP/validate-modules-960.ps1` holds the 960-row goldens). `DLSS5_NETWORK_HEIGHT=auto` picks the network tier from the input window (≤1280×720 → 720, ≤1600×900 → 900, else 1080; larger than 1920×1080 is rejected) and the FPS overlay shows the tier, e.g. `1600X900`; 720/900/1080 pin it. Runtime tiers via `DLSS5_SKIP_BLOCKS` in `native-game-flags.txt`: unset = full network; `42,43,46` (default) ≈ −1 ms at ≈41 dB; `12,28,41,42,43,44,46,52,53` (performance) another −0.8 ms at 900p (15.25 → 14.48 ms, 2026-09-17 ABBA) at ≈30 dB against the default output. `scripts/game-flags.txt` and `scripts/magpie-flags.txt` hold the two runtime configurations; `scripts/bench.ps1` compiles the shader set. See the [Magpie package instructions](scripts/package-README-magpie.txt) (Chinese).

## What is in this repository

| Directory | Content |
|---|---|
| `src/` | Standard ReShade add-on, image codecs and game integration; shared by Magpie and regular OptiScaler packages. |
| `hip/` | Shared HIP neural kernels and gfx1200/gfx1201 build recipes for all three packages. |
| `shaders/` | Image encoding/decoding and support shaders, plus the historical DX12 network. HIP builds still use some HLSL shaders. |
| `scripts/` | Add-on builds, package instructions and tracked defaults: `hip-game-flags.txt`, `hip-magpie-flags.txt`, and the new RE9 host overlay `re9-presr.ini`. |
| `Development/HIP/` | HIP host and D3D12 interop code, validation and experiments. Some files here are build dependencies; experiments are not automatically production changes. |
| `Development/RE9/presr/` | RE9-specific host/runtime adaptation: pinned upstream revision, patches, preparation/build/install scripts and evidence. The complete upstream host tree is not vendored here. |
| `Development/tools/` | Full-package assembly using verified framework baselines, model assets and matched modules. |
| `Development/results/`, `Development/deployments/` | Regression/performance evidence and deployment inventories. |
| `Development/DevHistory.md` | Completed development work; plans and limitations live in the respective topic documents. |
| `tools/` | Output comparisons and image statistics. |

**Source and complete distributions are managed separately.** Git contains our add-on/runtime/HIP sources and RE9 host patches. It does not contain the complete Magpie or regular OptiScaler framework source, or all model/framework assets needed to reproduce the full ZIPs. The RE9 host derives from [TheAutomatic's release/1.9.0](https://github.com/TheAutomatic/dlss-5-amd-project/tree/release/1.9.0); `upstream.json` pins its revision and `prepare-host.py` applies adaptations. Its GPL license is retained separately from this project's MIT code.

On the maintainer's machines, Linux holds this repository; Windows on the RX9070 system holds framework baselines, models and built artifacts. Complete releases are under `D:\給網友打包`; the RE9 host source/output are under `D:\DLSSNR-Lab\re9-presr\source` and `bin`, and HIP experiment artifacts under `D:\DLSSNR-Lab\hip-backend`. These are maintainer paths, not required user installation directories. New releases start from verified ZIPs, not a live game installation.

Integration: **Magpie / regular OptiScaler → dlss5-amd.addon64 → shared HIP kernels**; **RE9-specific OptiScaler → LmxxfNrRuntime.dll → the same HIP kernels**. The RE9 host and runtime must be used as a matched pair.

## How it works, briefly

- **Network**: pre-block (C32 @1920×1152) → encoder (C32 ×4, C64 ×4, C128 ×6, C256 ×8, C512 ×8) → 8 global ViT blocks
  (640 tokens × 1024) → decoder (C512 → C32, skip connections) → post-block 70 → RGB head. Window attention on 8×8
  windows, FFN with a 4× hidden layer, f16 residual stream quantized to E4M3 between blocks.
- **Kernels**: every GEMM is a wave-matrix multiply (16×32 A, 32×16 B, f32 accumulator) with E4M3 or f16 operands
  loaded straight from memory; row reductions (normalization, softmax denominators) are MMAs against an all-ones tile;
  quantization uses the hardware `Cast<F8_E4M3FN>`. The C32 attention runs QKV + attention + projection of two windows in
  one 256-thread group.
- **Game side**: the add-on hooks the FSR dispatch, encodes the frame, samples the previous network output through the
  motion vectors (temporal history), runs the network on a deferred submission ring (6 command lists per frame), and
  copies the result back. A small output-side temporal smoothing pass (`native_output_smooth.hlsl`) damps the shimmer
  the network adds around jittering edges.
- **Numerics**: an "exact" chain reproduces the NVIDIA kernels bit for bit (explicit f16 rounding after every step);
  the fast chain relaxes it (f32 accumulation, hardware rounding) and is validated against the exact chain by PSNR.

## Building

### HIP edition (0.20)

Requirements: Linux / WSL with `x86_64-w64-mingw32-g++`, ReShade 6.8 add-on headers and MinHook sources (for the DLL);
a Windows machine with an AMD driver that ships `amd_comgr_3.dll` and `amdhip64_7.dll` (for the kernels; no HIP SDK, no
DXC, no developer mode). The add-on's DX12 side still compiles the small HLSL helpers (codec, text overlay) at runtime with
the system `d3dcompiler`, which every Windows has.

```bash
bash scripts/build-addon.sh <minhook-src> <reshade-include> dlss5-amd.addon64 --hip   # the add-on, HIP backend
x86_64-w64-mingw32-g++ -std=c++17 -O2 -static hip/rtc_compile.cpp -o hip/rtc_compile.exe   # the kernel compiler
```

```powershell
# on the AMD machine: all 24 modules -> <out>\*.hsaco + modules.json + SHA256SUMS (about a minute)
powershell -ExecutionPolicy Bypass -File hip\build-modules.ps1 -OutputDir <out>
```

Install the modules as `DLSS5-AMD\native-game-tiled-assets\HIP\` next to the weights (or point `DLSS5_HIP_MODULES` at the
folder). `Development/HIP/validate-modules.ps1` runs the three bit-exact checks against a module set;
`Development/HIP/package-hip.ps1` assembles the game and Magpie packages. See `hip/README.md` for the recipe rules.

### DX12 editions (up to 0.15)

Requirements: Linux / WSL with `x86_64-w64-mingw32-g++` (cross build), Windows with an RDNA 4 GPU and a driver exposing
D3D12 wave matrices (linalg tier 10), the Shader Model 6.10 preview `dxc` (with `dx/linalg.h`), ReShade 6.8 add-on
headers, MinHook sources.

Where the preview pieces come from (all linked from Microsoft's post
[Announcing Agility SDK 1.721 preview and more Shader Model 6.10 features](https://devblogs.microsoft.com/directx/announcing-agilitysdk-721-preview-and-more-shader-model-6-10-features/)):
the preview DXC is a *preview* release of [microsoft/DirectXShaderCompiler](https://github.com/microsoft/DirectXShaderCompiler/releases)
(we use v1.10.2605.24, `dxc_preview_2026_05_22.zip`; unzip anywhere and pass the folder as `-DxcRoot`); the Agility SDK
runtime (`D3D12Core.dll`, folder `DLSS5-D3D12-721` in the package) is NuGet `Microsoft.Direct3D.D3D12` 1.721.3-preview;
the AMD driver is the RC "Agility SDK" build 26.10.07.02 (32.0.31007.2048), not a release driver: [download from AMD](https://drivers.amd.com/drivers/amd-software-adrenalin-edition-26.10.07.02-win11-rc7-agility-sdk.exe).
**Windows Developer Mode must be on** (Settings → System → For developers): the add-on enables the experimental shader models with
`D3D12EnableExperimentalFeatures`, which only succeeds in developer mode; without it the initialisation stops at its first step
(`sdk721_before_device ... experimental=` in `logs\native-submission-order.txt` is not `00000000`). Nothing else has to be installed
to run a release package: the shaders are precompiled.

```bash
# one click (Ubuntu / WSL): sudo apt install g++-mingw-w64-x86-64 git; fetches MinHook + ReShade headers into third_party/
bash scripts/build-addon-oneclick.sh            # -> native-game.addon64
# or by hand
bash scripts/build-addon.sh <minhook-src> <reshade-include> native-game.addon64 --tiled
bash scripts/build-bench.sh native-network70-temporal.exe
```

```powershell
# shaders only, any Windows x64 machine (needs the SM 6.10 preview dxc package; no GPU, no weights)
powershell -ExecutionPolicy Bypass -File scripts\compile-shaders.ps1 -Folder D:\dlss5-shaders -DxcRoot <dxc-preview>
# shaders + bench on the RX 9070 XT machine: <lab> holds the shaders, the weights and the bench exe
powershell -ExecutionPolicy Bypass -File scripts\bench.ps1 -Folder <lab> -DxcRoot <dxc-preview>
powershell -ExecutionPolicy Bypass -File scripts\deploy_fast.ps1 -Source <lab> -Dll native-game.addon64 -Flags scripts\game-flags.txt
```

## Changelog

Unless a Magpie scenario is specified, frame rates are Stellar Blade at 1920×1080 on an RX 9070 XT; "bench" is the offline test bench (network only). Every tag
after 0.01 keeps the bit-exact reference chain as its judge (≈ 42 dB PSNR against it); "bit-exact" below means the fast
chain's own output did not change by a single bit.

| Version | Date | What changed | Result |
|---|---|---|---|
| `0.01` | 09-08 | End of the exact port: all 71 blocks on wave-matrix kernels, bit-for-bit equal to the original network for 15 frames; weights resident in VRAM (no per-frame PCIe traffic); scratch shared between blocks (14.7 → 7.3 GB) | bench 186 ms, ~5 fps in game |
| `0.02` | 09-08 | Fast chain begins (exact chain frozen as the judge): FP32 hardware accumulation, E4M3 operands, activation epilogue and attention without intermediate f16 roundings; temporal path (motion vectors + previous output) hooked up in game | bench 112 ms, ~8 fps |
| `0.03` | 09-08 | Hardware f16/E4M3 conversions, fused QKV+normalize, C32 attention in two dispatches, ViT packed inputs, C512 direct attention, FP8 residual stream in the multi-head blocks | bench 62.7 ms, ~15 fps |
| `0.04` | 09-09 | Deferred submission ring, command-list batching (~100 → ~25 lists/frame), C32 attention with QKV folded in, noise prefix generated on the ALU instead of a 200 MB table, ViT QKV fused | game GPU 32 ms, 23–25 fps |
| `0.05` | 09-09 | Output-side temporal smoothing (the rain-scene shimmer), C32 attention two windows per group, ViT attention on FP8 | 24–25 fps |
| `0.06` | 09-09 | Repository restructured (`src/ shaders/ scripts/`), `bench.ps1` flattens the 76 nested runners, per-frame GPU probe off by default (its Flush cost 3 ms), pre-block output as E4M3 | 27–28 fps |
| (0.07) | 09-09 | User package only, no tag: three blocks skipped (40.7 dB), VRAM 6.8 → 3.75 GB with periodic MakeResident, C32 intermediates as f16, post-block merge folded into its FFN | 29 fps |
| `0.08` | 09-10 | C32 FFN fused into the attention prologue; tiled (non-power-of-two stride) layouts for ViT / C512 / decoder-entry weights; C512 FFWD output as E4M3 tiles read directly, C512 blocks mapped to the raster with an E4M3 stream between them (no window pack/crop, no QKV pack); post merge 4 channels per load; decoder projection epilogue with coalesced writes — all bit-exact. Rise of the Ronin via XeSS (`xessD3D12Execute` hook). Profiling toolchain (headless RGP capture, ISA statistics). Black-frame probe. Texture quality "High" or lower is now a stated requirement | bench 24.4 ms, 3.1 GB VRAM, 36–37 fps |
| `0.09` | 09-11 | Upsample projections 56/62/66 write f16 rasters read directly by the next block (bit-exact, −0.2 ms). **Magpie edition**: the add-on now loads in any process (the hard-coded exe whitelist that produced ReShade error 1114 in other games is gone), hooks the FSR 4 SDK loader's `ffxDispatch` as well, accepts 8-bit UNORM textures, scales motion vectors by the dispatch's `motionVectorScale`, and arms on a configurable frame (`DLSS5_SNAPSHOT_FRAME`), so it runs inside the SAOG0721 Magpie fork's FSR3 effect: any game in a 1920×1080 borderless window, no FSR/DLSS support needed (~30 fps; 8-bit sRGB input, so the picture is brighter than the in-game hook). ViT expand+contract fusion tried and rejected (2× slower, latency-bound) | bench ≈24.2 ms, 36–37 fps in game; Magpie ≈30 fps |
| `0.10` | 09-11 | Black-block root cause fixed: the hardware E4M3 cast does not saturate, so a residual beyond ±448 became NaN, the NaN token spread over its 8×8 attention window and the rgb head clamped it to 0. The fused C32 block now clamps to ±448 before its hardware casts (`DLSS5_BUILD_C32_SAT_CAST`, FFN input / hidden / attention input / AV output). Bit-identical on the reference fixture; the Magpie dump frames go from 25920 NaN head values to 0. Windows Developer Mode documented as a requirement (`D3D12EnableExperimentalFeatures`). Magpie bundle `Magpie-DLSS5-AMD-0.10.zip` | unchanged |
| `0.11` | 09-11 | Take-over time 20-30 s → ~3.5 s: weight files prefetched into memory when the add-on loads (`NativePrefetchWeights`), the ~1000 resident weight copies batched into one GPU wait instead of one queue+wait per table (`NativeResidentBatch`; the first version released a copy destination early and hung the GPU — both ends are now held until the flush), the six runtime-compiled shaders cached on disk (`shader-cache\`), f16 weight expansion on 8 threads. Numerically unchanged (reference fixture bit-identical). Init timing probes (`DLSS5_VRAM_LOG=1` / `DLSS5_INIT_LOG=<file>`). Two-pass C32 softmax tried and kept off (null: the 896-byte scratch belonged to a PSO that is never dispatched; the fused kernel has none). Magpie bundle `Magpie-DLSS5-AMD-0.11.zip` | unchanged |
| `0.12` | 09-12 | On-screen notice (`native_text_overlay.h` / `.hlsl`): when the upscaler's output is not 1920×1080 (a 2K/4K screen with Magpie set to fit the screen, or a non-1080p game window) the add-on writes "DLSS5-AMD: INPUT MUST BE 1920X1080 (NOW WxH)" into the picture instead of silently watching; "INITIALIZING..." during the 3-5 s take-over and "INIT FAILED - SEE DLSS5-AMD\LOGS" when initialization fails (developer mode off, wrong driver). A 5×7 bitmap font drawn into our own buffer and copied into the host texture on our own command list after the game's batch (a UAV on the host texture or recording into the game's list crashes D3D12Core in Magpie). `DLSS5_NOTICE=0` in the flags file turns it off. Also: `DLSS5_OVERLAP` (network on its own compute queue, one frame behind; null on this GPU, default off) and `DLSS5_BUILD_C32_LDS_SLIM` (fused C32 kernel with 4 KB less LDS; bit-identical, no gain, default off). Numerically unchanged. Magpie bundle `Magpie-DLSS5-AMD-0.12.zip` | unchanged |
| `0.13` | 09-12 | `DLSS5_SHOW_FPS=1` (on in the Magpie bundle): the network's own frame rate drawn in the corner with the notice font. The hook now takes over the upscaler output in whatever state the game declares for it (mapped ffx_api state bits), not only UAV. Pre-block errors carry the source line. Found the hard way: Windows Update silently replaces the preview driver with the release one (SM 6.10 gone, every PSO fails with E_INVALIDARG, the screen says INIT FAILED) -- reinstall 26.10.07.02 and set `ExcludeWUDriversInQualityUpdate=1`. The Magpie bundle's effect group now has XeSS Frame Generation (ZeroMV, vendor-agnostic) after FSR3_SR: 28 real → 55 presented fps on the 9070 XT, one frame of latency, the network itself ~20% slower next to the optical flow. Numerically unchanged. Magpie bundle `Magpie-DLSS5-AMD-0.13.zip` (sha256 9104C48D…) | unchanged |
| `0.14` (bundle) | 09-12 | FPS display: update at intervals of at least three seconds, reuse the unchanged text strip, and copy it at the end of the existing output submission instead of a separate synchronous submission. XeSS FG ZeroMV remains enabled in the preset. Remove backup DLLs, logs and shader caches from the bundle; regenerate file checksums. `Magpie-DLSS5-AMD-0.14.zip`, 358,004,639 bytes; SHA256 `14ccde3c752b40821cb9f30024579304627a2499e087e06e9aec399bfe734eed`. No 0.14 tag yet. | Build passed; 671 archive files verified; FPS gain not measured |
| [0.15](https://pan.quark.cn/s/1601ca8f80ae) | 09-13 | Accept ordinary windows with width ≤1920 and height ≤1080; fit smaller inputs to the fixed network surface while preserving aspect ratio, then restore the source extent before FSR4 fills the screen. Portable preset: FSR3 (the DLSS5 entry point) → FSR4 fill screen → XeSS FG ZeroMV. `DLSS5_FIT_INPUT=1`; retain the three-second FPS display. Bundle `Magpie-DLSS5-AMD-0.15.zip`.  358,010,545 bytes; SHA256 `9bb7a021d09d987986f96dbd920589018606c9800dbd08e007f4b309388e5909`.| 672 archive files verified; Onimusha Medium at 2K ~30 fps |
| [0.15-900P](https://pan.quark.cn/s/a5339e4c8549) | 09-14 | Fixed 1600×900 inference (1600×1024 processing, 400 ViT tokens), followed by FSR4 scaling; AMD optical flow enabled only on the DLSS5/FSR3 item. User reports better image quality than 720p and steadier frame rates than 1080p with FG. Isolated inference is about 16.71 ms, not game frame time. Bundle `Magpie-DLSS5-AMD-0.15-900P.zip`, 358,038,890 bytes; SHA256 `718d77941674d6e851e7babc14b40a596da52e86aec603f44f956b99ff6811d5`. | 900p gameplay tested by user; 676 archive files verified |
| [0.20](https://pan.quark.cn/s/3c8b5329353c) (HIP) | 09-17 | HIP backend: COMGR-compiled gfx1201 kernels (sources and build recipe in `hip/`, experiments in `Development/HIP/`), D3D12↔HIP shared buffers/fences, bit-exact with the DX12 chain. Kernel-level work of 09-16/17 (ISA-driven: branchless conversions, batched loads, hoisted reloads, prepacked residual diagonals, inlined prefix) brought the isolated 900p frame from 19.4 to ≈15.5 ms, 8% faster than the DX12 chain; in-game 900p 52 fps. Packages `DLSS5-AMD-0.20.zip` (game) and `Magpie-DLSS5-AMD-0.20.zip` (Magpie, no Agility runtime). Requires `amdhip64_7.dll` from the AMD driver. |
| [0.21](https://pan.quark.cn/s/85a507a744bd) (HIP) | 09-17 | `DLSS5_NETWORK_HEIGHT=auto`: network tier chosen from the input window (≤1280×720 → 720, ≤1600×900 → 900, else 1080), the FPS overlay shows the tier (`1600X900`); package notes: measured 1.2 GB VRAM, release driver reported working, performance tier (`DLSS5_SKIP_BLOCKS` nine-block set, −0.8 ms at ≈30 dB). Kernels, weights and output identical to 0.20. In play: 900p 52–54 fps, 1080p 37–38 fps. Packages `DLSS5-AMD-0.21.zip` (sha256 38e15189…) and `Magpie-DLSS5-AMD-0.21.zip` (sha256 8eeee2dd…). |
| [0.22](https://pan.quark.cn/s/03f9995d0551) (HIP) | 09-17 | 900 tier padded to 960 rows instead of 1024 (60 reflected rows + one zero-token row, the 1080 tier's scheme): same kernels, −0.9 ms (6%, 15.8 → 14.9 ms same batch; ≈14.4 ms on the quiet machine), 900p ≈ +3 fps. Output differs from 0.21 (31.5 dB, both layouts are self-defined); `DLSS5_NETWORK_HEIGHT=900w` restores the 0.21 layout. New 960-row goldens (`validate-modules-960.ps1`). Packages `DLSS5-AMD-0.22.zip` (sha256 59226956…) and `Magpie-DLSS5-AMD-0.22.zip` (sha256 8186b67d…). |
| 0.23 · [Magpie](https://pan.quark.cn/s/548e52cc4f49) · [OptiScaler](https://pan.quark.cn/s/8b5a402012a2) (HIP) | 09-18 | Fix for hosts with an iGPU (AMD Radeon(TM) Graphics) or a second GPU: initialization failed with `bridge currently requires exactly one HIP GPU` (INIT FAILED on screen, user report 2026-09-18). The bridge now enumerates the HIP devices and picks the one whose name matches the game's D3D12 adapter (first match; two identical cards would still pick the first). Single-GPU hosts are unchanged; kernels, weights and output identical to 0.22 (Stellar Blade 1080p 37 fps, 900p 52 fps re-checked). Packages `DLSS5-AMD-0.23.zip` (sha256 3dde0e0a…) and `Magpie-DLSS5-AMD-0.23.zip` (sha256 7146569c…). Added 09-19: `OptiScaler-DLSS5-AMD-0.23.zip` (sha256 9d70d28f…), bundling OptiScaler 0.9.4 + ReShade + the same 0.23 HIP add-on. Tested in Stellar Blade with FSR inputs and both FSR 2.1 and FSR 3.x/4 backends; defaults to FSR 3.x/4, frame generation off. Other games remain unverified. |
| 0.24 · [OptiScaler](https://pan.quark.cn/s/1f32ffbd2e96) (HIP) | 09-19 | Pre-upscale path: low-resolution game color → DLSS5 → OptiScaler FSR 3.x/4 → display output. Changes our add-on, not OptiScaler or the network kernels/weights. Same-queue asynchronous submission; tested in Stellar Blade at 2560×1440, FSR Quality (1707×961 input), about 34–35 fps in play. DLSS5 history is reset every frame for now; FSR temporal processing remains enabled. Network input must still fit within 1920×1080; 4K output and Magpie regression are not yet verified. Package `OptiScaler-DLSS5-AMD-0.24.zip` (385,880,495 bytes; sha256 2a46adeb…). |
| 0.24.1 · [OptiScaler](https://pan.quark.cn/s/4f73a54d0ff9) (HIP) | 09-19 | Asset/config lookup fix: when `DLSS5-AMD` is absent beside a relocated add-on DLL (for example under `_storage_`), also check beside the game executable before falling back to the development directory. Rechecked the pre-upscale chain in Stellar Blade at 2560×1440; network kernels and weights unchanged. This does not resolve Resident Evil Requiem’s same-command-list compatibility issue. Package `OptiScaler-DLSS5-AMD-0.24.1.zip` (385,883,920 bytes; sha256 1e9ec721…). |
| 0.24.2 · [OptiScaler](https://pan.quark.cn/s/f74aaa5c7f9a) (HIP) | 09-19 | Skip idle per-draw configuration lookups and job-map locking, and avoid log counter contention after the quota. F6 off bypasses new pre-upscale captures/color copies while draining already captured work once. Stellar Blade city test recovered to about 49 fps (previously about 31); synchronous/asynchronous GPU checks passed. Kernels and weights unchanged. Package `OptiScaler-DLSS5-AMD-0.24.2.zip`. Full package rebuilt the same day to fix FPS/status visibility settings; download link updated. |
| 0.25 · [Magpie](https://pan.quark.cn/s/09630ed99606) · [OptiScaler](https://pan.quark.cn/s/636691131c5f) (HIP) | 09-19 | **Optimizations**: reuse C32/multihead attention exponentials and simplify reciprocal calculation; pass intermediate features and decoder outputs as FP8 bytes to reduce data movement; use a fast path for full decoder tiles. **Fixes/support**: fix missing 900-tier tail writes and Unicode-path loading; add gfx1200 kernels for RX 9060/XT with automatic gfx1200/gfx1201 selection. RX 9070 XT regression passed; RX 9060/XT awaits hardware feedback. Magpie at 1080p with DLSS5 only measured about 37 fps, roughly unchanged. Full packages available for both Magpie and OptiScaler. |
| 0.26 · [Magpie](https://pan.quark.cn/s/7ce2ca11db43) · [OptiScaler](https://pan.quark.cn/s/c880a70f0824) (HIP) | 09-19 | FFN reads FP8 byte fragments directly, removing input staging and two barriers; C256 weights are prepacked into contiguous matrix fragments at initialization to reduce scattered loads and byte assembly. Include the missing R11G11B10 decoder shader to fix black output at lower Effects Quality in Lies of P, confirmed by user testing; add shader compilation/binding checks. Both full packages built; archive contents and 44 shader variants verified. |
| 0.26.1 · [OptiScaler-REFramework](https://pan.quark.cn/s/624c87a6aa11) (HIP, special-purpose build) | 09-20 | **For unusual integration cases such as RE9; not the standard release. Use the general package for ordinary games. Only Resident Evil Requiem has been tested.** Post-FSR HIP compatibility with R10G10B10A2/FP16 conversion, a fixed 900p network and a 1080p SDR output limit. Status, resolution and Present FPS overlay with F7 visibility control. Includes REFramework, OptiScaler, ReShade, complete model assets and gfx1200/gfx1201 kernels; retains 0.26 optimizations. User gameplay validation passed. |
| 0.27 · [Magpie](https://pan.quark.cn/s/ec3a3282aa76) · [OptiScaler](https://pan.quark.cn/s/004278159ed8) · [OptiScaler-REFramework](https://pan.quark.cn/s/010683548f68) (HIP) | 09-20 | Exact streaming ViT attention reduces intermediate storage and repeated reads. Optional R3 adaptive reuse adds change checks, identical-input cache extension and fused anchor updates; disabled by default. Defaults are copied from tracked per-variant templates. Full model/runtime payloads and gfx1200/gfx1201 modules; no INT4 or pruning. REFramework retains fixed 900p / max1080p SDR post-processing. |
| 0.28 · Magpie / OptiScaler / OptiScaler-REFramework (HIP; download links pending upload) | 09-22 | Six lossless kernel improvements: RGB read sharing, C128/C256 zero-padding shortcuts, fixed-shape ViT expansion/projection and decoder projection. Stellar Blade gameplay/FPS essentially unchanged. RE9 gains a matched pre-SR host, same-frame exposure and initialization preparation, with tested2K borderless output. Regular hosts unchanged. Full packages; RE9 includes corresponding modified host source and TheAutomatic credit. |

## Weights

The network weights are NVIDIA's. The runtime weight files the host code loads (`block31-expand.f32`,
`post70-attention.f32`, … about 16 GB with the reference dumps) are not in this repository; they were extracted from a
locally owned copy of `nvngx_dlssnr.dll` with the scripts in `Development/` (`prepare_native_*_gpu.py` and the
per-block notes), which document the layouts but are not a polished pipeline. No NVIDIA DLL is distributed here.

## Authors

Kien — direction, game integration, testing. The reverse engineering, kernels and optimization were
written with AI collaborators (Claude, GPT); the working notes in `Development/` are theirs. Write-ups (Chinese): [WeChat, DLSS5 series](https://mp.weixin.qq.com/mp/appmsgalbum?__biz=MzYzMzMwNzk0NA==&action=getalbum&album_id=4687269655390453762#wechat_redirect). Resume / 简历: [here](https://github.com/lmxxf/ai-theorys-study/blob/main/resume/README.md).

## License

Code in this repository is released under the MIT License. NVIDIA binaries and weights are not covered by it.
