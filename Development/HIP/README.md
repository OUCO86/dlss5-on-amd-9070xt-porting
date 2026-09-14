# HIP backend development

Experimental HIP branch; installed Magpie/Stellar Blade and release packages still use the validated 900P HLSL backend.

The complete 512×512 graph (blocks0–70) passes bitwise comparison against the existing original-network RGB oracle, both scalar and `--wmma`. Output:786432 float32 values, zero differences/nonfinite values, SHA256 `bd52c601b68c4ed27f271cd2c7bcffc8511519f652534f2a0c51ffa9450e6da4`. This is a numerical development runner, not a realtime addon.

## Build and run

The compiler in [TOOLCHAIN.md](TOOLCHAIN.md) uses the installed Windows COMGR3 DLL; HIP SDK headers/libraries are unnecessary. Runtime uses System32 HIP7. Tested on RX9070XT/gfx1201 with driver32.0.31007.2048. Formal-driver testing remains outstanding.

Compile `c32_reference.hip` concatenated with `prefix_reference.hip` as `c32_prefix_reference.hsaco`. Compile remaining sources separately as `multihead-reference.hsaco`, `deep_reference.hsaco`, `boundary_reference.hsaco`; WMMA sources become `c32_wmma.hsaco`, `multihead-wmma.hsaco`, `deep_wmma.hsaco`. Keep all ten in MODULES.

Build host with `x86_64-w64-mingw32-g++ -std=c++17 -O2 -static Development/HIP/reference_network.cpp -o reference_network.exe`.

Run on Windows:

```
reference_network.exe ASSETS MODULES INPUT_RGBA_F32 NOISE_F32 OUTPUT_RGB_F32 --wmma
```

Default512×512/postshift0 matches the checked oracle. `--720` selects1280×768/240 tokens; `--900` selects1600×1024/400 tokens; `--1080` selects1920×1152/640 tokens. All use postshift3 by default. 900P WMMA matches the HIP scalar graph bitwise on the tiled test image; 720P/1080P complete HIP graphs have not yet been verified. Input/history contain the full processing grid; output is RGB float32. Optional `--seed N`, `--history FILE`, `--post-shift 0..3`, `--dump EXISTING_DIRECTORY`, `--runtime 6|7`. Use runtime7 for the validated path. Omit `--wmma` for scalar reference matrices. Keep original f32 weights, or their exact f16 cache; noise contains50331648 floats.

`--pooled` reuses dead tensor allocations on the single HIP stream and removes per-kernel CPU waits. Uploads/dumps/final readback still wait explicitly. `--repeat N` repeats the same input without temporal feedback; `--profile` reports HIP event totals per kernel. Negative/nonfinite event intervals invalidate an iteration (observed at cold startup). Reported wall time includes uploads/readback and host work; it is not game FPS. Live integration and formal-driver verification remain unfinished.

`build-modules.ps1 -Compiler PATH_TO_RTC_COMPILE_EXE -OutputDir DIRECTORY` assembles and compiles all ten modules from this directory.

## Validation

Standalone probes cover D3D12/HIP shared memory and fences, native WMMA/HLSL arithmetic, prefix, C32, multihead and deep kernels. See their source CLI and ABI documents. GPU tests run serially. HLSL oracle executables require the existing preview SDK; HIP inference and interop do not enable experimental D3D12 features. Logs and binary captures live under ignored `release/HIP/`; results and limitations are recorded in [DevHistory](../DevHistory.md).

`--wave` loads `wave-pointwise.hsaco` (c32_reference + wave_pointwise) for cooperative Q/K normalization and probability rows. Eight wave32 rows per256-thread block; host multiplies reference row counts by32. Both512 and900 complete graph outputs retain their bitwise reference hashes. Original H/F arithmetic and reduction order are preserved.

`-IsaHalf` on the build script enables explicit gfx12 `v_cvt_f16_f32` / `v_cvt_f32_f16` assembly boundaries. Unlike a plain `_Float16` cast, this retains complete512/900 output parity under COMGR optimization. Default software H remains available as the reference. `half_probe.hip` + `half_validate.cpp` isolate conversion behavior across1258048 finite float inputs.

`--tiled` additionally loads c32_tiled and multihead-tiled modules for shared FP8 operand staging. Complete512 and900 exact-reference hashes are unchanged. Cold/warm timings and isolated-tail validation are in DevHistory; use `-IsaHalf` consistently when comparing performance.

`Network::SetNoise` and `Enqueue` provide a device-pointer path. `device_network.cpp` verifies uploads/readback outside repeated inference. `hip_d3d12_bridge.h` and `bridge_network.cpp` verify D3D12 shared buffers/fences through the complete900 graph without experimental DirectX features. The bridge currently requires one HIP GPU matching the D3D12 adapter and serialized frames. This is an offline verified bridge, not an installed game addon.

`hlsl_network_oracle.cpp` runs the existing900 production HLSL network on the same processing-grid floats, seed0/postshift3/no history. Production fast flags change Gaussian generation and intermediate rounding, so this output currently differs from the exact HIP graph (RMSE0.01514 on the tiled fixture). Separate production-fast HIP kernels are being developed; exact-reference parity must not be described as production-fast parity.

Experimental addon build: `bash scripts/build-addon.sh third_party/minhook third_party/reshade/include release/HIP/dlss5-hip-candidate.addon64 --hip`. This compile-time switch selects NativeHipNetwork, skips SDK721/experimental-SM setup and keeps ordinary D3D12 codec/temporal passes. Modules default to ASSETS/HIP; `DLSS5_HIP_MODULES` overrides the path. The same switch can compile the existing720p benchmark for a full frame test. Independent900 temporal frame testing passed with5760000 finite history floats, but the exact backend is still about137ms per frame and the candidate has not been installed into a game.
