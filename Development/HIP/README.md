# HIP backend development

The HIP branch contains a complete GPU inference backend and an experimental D3D12 bridge/addon. Magpie retains the validated900P HLSL release. On2026-09-15, the user requested and received the experimental HIP candidate in Stellar Blade; rollback instructions are below.

| Path | Verified result | Remaining limitation |
|---|---|---|
| Exact512 graph |786432 RGB float values bitwise equal to original oracle|Offline reference/performance development|
| Exact900 graph |WMMA equals HIP scalar, including pooled execution|Uses original precision schedule, distinct from shipped fast HLSL|
| Production operator families |True HLSL comparisons passed for C32, MH, ViT, split, decoder and pool|Whole fast graph still differs from production output|
| GPU pointer/D3D12 bridge |Complete900 graph round-trips with identical output; temporal frame test passed|Candidate not installed; formal driver not tested|

Exact512 SHA256: `bd52c601b68c4ed27f271cd2c7bcffc8511519f652534f2a0c51ffa9450e6da4`. Latest fast900 offline hot wall time is about70–72ms, with1.9GiB graph allocations. This is slower than the existing HLSL release. Whole fast output RMSE is about0.00927 against the shipped HLSL on the tiled fixture; it is not accepted as production parity. See [DevHistory](../DevHistory.md) for test conditions, failures and later updates.

## Build

[TOOLCHAIN.md](TOOLCHAIN.md) describes the SDKless COMGR compiler. It uses installed Windows COMGR3; headers/device libraries and experimental DirectX are unnecessary for HIP compilation/execution. Tested GPU: RX9070XT/gfx1201; runtime: System32 `amdhip64_7.dll`; driver32.0.31007.2048. HIP6 explicitly failed in a separate attempt, so there is no automatic fallback. Official [HIP SDK release notes](https://rocm.docs.amd.com/projects/install-on-windows/en/latest/about/releasenotes.html) and actual formal-driver verification are separate evidence.

On Windows, with sources available locally:

```powershell
.\build-modules.ps1 -Compiler PATH_TO_RTC_COMPILE_EXE -OutputDir MODULE_DIRECTORY -IsaHalf -Fast
```

`-Fast` includes experimental production and fused kernels; omit it for reference modules only. A source/code SHA256 manifest is written as `modules.json`. Build all matching modules before running a newly built host; changed kernel contracts must not be mixed with old code objects.

Linux host cross-build:

```sh
x86_64-w64-mingw32-g++ -std=c++17 -O2 -static Development/HIP/reference_network.cpp -o reference_network.exe
```

## Run offline

```text
reference_network.exe ASSETS MODULES INPUT_RGBA_F32 NOISE_F32 OUTPUT_RGB_F32 --wmma --wave --tiled --pooled
```

Default512×512/postshift0 matches the original oracle. `--720` selects1280×768/240tokens; `--900`1600×1024/400tokens; `--1080`1920×1152/640tokens. Input/history are full processing-grid RGBA floats; output is RGB floats. Full720/1080 HIP validation remains pending.

Experimental fast900 arguments additionally use:

```text
--900 --fast-prefix --fast-deep --fast-mh --mh-wave --fused-c32 --fused-ffn --fused-mh --skip-blocks 42,43,46
```

Options: `--repeat N`, `--seed N`, `--history FILE`, `--post-shift 0..3`, `--dump EXISTING_DIR`, `--dump-only comma,separated,stages`. `--profile` collects HIP events, but negative intervals have occurred even after warmup; an invalid iteration must be discarded. Wall timing includes host work and transfers. No test figure is game FPS.

Gaussian fast math has small measured sin/cos differences; its projection is independently exact on supplied HLSL features. Each conversion site follows its actual production contract: explicit legacy half conversions oftenRTZ, matrix half casts and selected software helpersRNE. Keep the original reference path for comparisons.

## Integration and diagnostics

`device_network.cpp` checks persistent GPU-pointer inference. `bridge_network.cpp` checks shared D3D12 resources/fences without preview DirectX. The bridge requires one HIP GPU matching the D3D12 adapter and serialized calls. `Network::Enqueue` forbids host observers/readback diagnostics.

```sh
bash scripts/build-addon.sh third_party/minhook third_party/reshade/include release/HIP/dlss5-hip-candidate.addon64 --hip
```

The compile-time HIP switch preserves ordinary D3D12 codec/temporal passes and skips SDK721/experimental-SM setup. Modules default to ASSETS/HIP, overridden by `DLSS5_HIP_MODULES`. The addon defaults to the exact backend; `DLSS5_HIP_FAST=1` explicitly selects the experimental fast/fused/prepacked path. Whole-graph production parity remains outstanding.

`hlsl_network_oracle.cpp` uses Agility721 only as the production HLSL oracle. `replay_prefix.cpp` is a deliberately labelled diagnostic that injects captured block0/4 states to locate divergence; it must never be presented as normal end-to-end verification. Other validators and their ABI documents describe each independently tested family. Captures, logs, executables and code objects belong in ignored `release/HIP/`.

## 2026-09-15 weight prepacking

`--packed-weights` enables lossless initialization-time FP8 packing for MH dense matrices and, when `--fast-deep` is active, ViT FP8 linear / split projection matrices. Build with `-Fast -IsaHalf` to include the three `*-packed.hsaco` variants. Original paths remain available for A/B comparison.

Matrix bytes occupy the beginning of their original float regions. Biases/scales and region offsets stay unchanged; unused padding remains allocated in this first version. This reduces matrix reads/conversions, **not total weight allocation by four times**. FP16-only matrices keep their original representation. Non-FP8-exact coefficients are rejected rather than requantized.

`benchmark-packed-weights.ps1` runs baseline/packed/packed/baseline with a fresh process per leg, excludes the cold first iteration, checks full output SHA256 and writes timings.csv. On the900 fixture, MH-only gave no clear gain (70.413→70.222ms); adding ViT/split FP8 matrices gave70.4165→65.217ms median hot wall time, ten samples per variant. All outputs equal baseline `7b959143…`; this preserves existing output, not a new claim of matching HLSL. Seed123 with supplied history also matches baseline. Current game installs are unchanged.

## Stellar Blade trial installation (2026-09-15)

Installed DLL SHA256 `0202b4dc4ff94bb0a80300b3488b2b6e7ae942d0e4a58021c941d5924be40bba`, fast900P+packed weights, including the ReShade/native COM identity fix. Game-local DLSS5-AMD contains isolated flags/logs/23 modules and an asset junction to the validated lab asset set. Global flags, Magpie and drivers were not changed. Full temporal frame check passed at about63ms per frame; actual game validation belongs to the user trial.

After closing the game, run `D:\DLSSNR-Lab\hip-backend\stellarblade-hip\restore-stellarblade.cmd` to restore the backed-up900P HLSL DLL and disable the local HIP root. F6 only bypasses neural processing to the game's own FSR; it does not restore the old DLL.

### C32 native RTZ and diagnostics (2026-09-15)

The reference runner now accepts --wall-profile. It drains before each kernel
and measures launch through completion with a monotonic CPU clock. Reported
serialized_kernel_ms includes submission/wait overhead and changes scheduling;
it identifies candidates, not pure GPU time or normal frame percentages.
Device-only game inference rejects this diagnostic mode.

C32 fused FFN/attention defaults HIP_C32_RTZ_ISA=1, replacing software truncation
with hardware RTZ. Define 0 for the old path. test_rtz.cpp and rtz_probe.hip
validated 1,186,626 finite inputs including half boundaries. The ABBA runner
benchmark-module-swap.ps1 checks complete output hashes: seed0 65.260→61.0745ms,
seed123 65.5015→61.2275ms, identical outputs in each comparison. These are offline
wall timings. No installed module was replaced. HIP_C32_LDS_VECTOR remains an
optional disabled experiment: it showed no whole-network gain.

### Native FP8 conversion and C32 packed weights (2026-09-15)

Fast kernels default HIP_NATIVE_FP8_F=1; deep/boundary also default
HIP_NATIVE_RTZ=1. Define either as 0 for legacy conversion. The finite-domain
FP8 comparison passes 1,186,626 boundary/random inputs. Saturation and input
signed-zero normalization are explicitly preserved.

The runner supports --packed-c32 for fused FFN/attention weights; HIP_FAST now
selects it in the game adapter. A matching c32_fused_ffn_attention-packed.hsaco
is required (24 modules in a complete build). Scales/bias remain float32 at the
original offsets. Normal and packed modules must not be interchanged.

Combined offline ABBA: 61.1815→58.990ms at seed123 with equal output hashes.
The DLL compiles, but these changes have not been installed into the game.
See DevHistory for separate conversion/packing measurements and limitations.

### Byte-sized normalized QKV (2026-09-15)

--fp8-normalized requires fast MH, wave normalization and fused attention.
The producer mh_qkv_normalize_fast_wave_fp8 writes one E4M3 byte per element;
mh_attention_fused_fp8 consumes those bytes directly. Original raster
[pixel][Q,K,V][channel] indices and arithmetic are preserved. Only this tensor's
allocation is quartered; the pool's total capacity need not fall by the same
factor. Original float exports remain available.

HIP_FAST enables this path. Rebuild both multihead-fast-padded-wave-packed and
multihead_fused_attention: an older 24-module set lacks the new exports.
900 offline ABBA: 58.8955→55.3815ms with identical final RGB; explicit history
fixture: 60.177→56.7405ms, also identical. These are not game FPS measurements.
