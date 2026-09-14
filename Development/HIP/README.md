# HIP backend development

Experimental HIP branch; installed Magpie/Stellar Blade and release packages still use the validated 900P HLSL backend.

The complete 512×512 graph (blocks0–70) passes bitwise comparison against the existing original-network RGB oracle, both scalar and `--wmma`. Output:786432 float32 values, zero differences/nonfinite values, SHA256 `bd52c601b68c4ed27f271cd2c7bcffc8511519f652534f2a0c51ffa9450e6da4`. This is a numerical development runner, not a realtime addon.

## Build and run

The compiler in [TOOLCHAIN.md](TOOLCHAIN.md) uses the installed Windows COMGR3 DLL; HIP SDK headers/libraries are unnecessary. Runtime uses System32 HIP7. Tested on RX9070XT/gfx1201 with driver32.0.31007.2048. Formal-driver testing remains outstanding.

Compile `c32_reference.hip` concatenated with `prefix_reference.hip` as `c32_prefix_reference.hsaco`. Compile remaining sources separately as `multihead-reference.hsaco`, `deep_reference.hsaco`, `boundary_reference.hsaco`; WMMA sources become `c32_wmma.hsaco`, `multihead-wmma.hsaco`, `deep_wmma.hsaco`. Keep all seven in MODULES.

Build host with `x86_64-w64-mingw32-g++ -std=c++17 -O2 -static Development/HIP/reference_network.cpp -o reference_network.exe`.

Run on Windows:

```
reference_network.exe ASSETS MODULES INPUT_RGBA_F32 NOISE_F32 OUTPUT_RGB_F32 --wmma
```

Default512×512/postshift0 matches the checked oracle. `--1080` selects1920×1152/postshift3 but that complete HIP geometry has not yet been verified. Input/history contain the full processing grid; output is RGB float32. Optional `--seed N`, `--history FILE`, `--post-shift 0..3`, `--dump EXISTING_DIRECTORY`, `--runtime 6|7`. Use runtime7 for the validated path. Omit `--wmma` for scalar reference matrices. Keep original f32 weights, or their exact f16 cache; noise contains50331648 floats.

Each current kernel synchronizes; tensors allocate/free individually and weights upload lazily. Reported wall time includes these costs. Buffer reuse, frame scheduling, live integration and formal-driver verification are unfinished.

## Validation

Standalone probes cover D3D12/HIP shared memory and fences, native WMMA/HLSL arithmetic, prefix, C32, multihead and deep kernels. See their source CLI and ABI documents. GPU tests run serially. HLSL oracle executables require the existing preview SDK; HIP inference and interop do not enable experimental D3D12 features. Logs and binary captures live under ignored `release/HIP/`; results and limitations are recorded in [DevHistory](../DevHistory.md).
