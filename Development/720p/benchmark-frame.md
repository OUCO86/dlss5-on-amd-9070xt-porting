# Native 720p / 1080p inference benchmark

Cross-build from the repository root:

```sh
x86_64-w64-mingw32-g++ -w -std=c++17 -O2 -static -municode -Isrc Development/720p/benchmark_frame.cpp -o Development/720p/benchmark_frame.exe -ld3d12 -ldxgi -ld3dcompiler -ldxguid
```

The EXE needs the existing Agility SDK 721 `D3D12` directory beside it, experimental shader support, and an AMD GPU. Use an isolated test directory with `DLSS5-AMD/native-game-flags.txt` and `DLSS5-AMD/logs/` beside the EXE, so runtime diagnostics resolve locally. Never overwrite the released DLL or deployed shader assets. Assets must contain matching branch shaders, weights, `noise.f32` (or `.f16`) and `normalized-output.f32` for temporal sampling.

Arguments:

```text
benchmark_frame.exe ASSETS FLAGS 720|1080 OUTPUT_PREFIX [frames=30] [temporal=1]
```

Run each height in a separate process against the same flags and matching isolated assets. Output prefix's parent must already exist. Close other GPU workloads for ceiling measurement. Temporal mode defaults on with zero-motion RG16F input and a deterministic fixed gradient/checkerboard source. Each iteration restores that frozen source before timing. This exercises history reuse without recursively feeding already-processed color back into inference.

The harness loads flags into both narrow and wide CRT environment tables, then overrides network height, disables debug dumps, black/game probes, FPS overlay, per-submission probe, and overlap queues. Three warmups are excluded. CSV records every sample; stdout reports mean/median/min queue elapsed and reciprocal mean/min FPS, plus CPU wall time. Queue timestamps surround the actual encode/network/decode submissions and final copy. They include submission gaps and exclude source restoration, initialization, game rendering, capture, FSR4 and frame generation: these numbers are native inference throughput, not game FPS.

PPM output and RGB extrema/mean check final visible color variation. An extra unmeasured temporal frame dumps history/motion/warped/color and checks floating-point history for NaN/Inf. UNORM color alone cannot prove internal finite values; history check is available only with temporal mode. GPU work is fenced before resource release and readback. The benchmark does not estimate visual quality from the synthetic scene.

`temporal=0` keeps the production temporal-capable graph but resets history on every frame; it does not instantiate an incompatible non-temporal shader layout.
