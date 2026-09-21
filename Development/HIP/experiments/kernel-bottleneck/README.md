# Per-kernel counter capture

prepare.py makes isolated headers/benchmark under/tmp/kernel-bottleneck, repeats the first DLSS5_COUNTER_TARGET call10000 times and logs its original launch index. The mixed-API capture.ps1 path is retained ONLY to reproduce an invalid-output capture; do not use its metrics as normal workload evidence.

prepare-pure.py generates dump.cpp (normal benchmark plus DLSS5_BENCH_BRIDGE_ISOLATE, saves counter-input/expected.f32) and pure.cpp. Compile dump with standard HIP benchmark defines and D3D libraries; pure with C++17/static, -I/tmp/kernel-bottleneck, no D3D linking/context. NativeHipNetwork option setup is copied, post_shift3 hardcoded to actual Frame contract. Run no-profile pure control and verify bitdiff0 before capture-pure.ps1. Names: dump_counter_input.exe, pure_kernel_counter.exe; same lab modules/flags as captured controls. Source/expected inputs are generated assets outside git.

capture-pure.ps1 guards games, captures16 dispatches from3000, keeps2000 frames alive, verifies first/final raw outputs. Diagnostic repeated work is NOT performance timing. Source memory and weights become hot; interpret counters accordingly. Existing pipeline-gap/read-counters.py parses/cross-checks derived counters. See results/kernel-bottleneck-20260921.
