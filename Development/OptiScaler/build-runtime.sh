#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
host=/tmp/re9-upstream-bridge-review
runtime="$host/OptiScaler-DLSSNR-PreSR-Multipass-main/OptiScaler/dlssnr/backend/lmxxf_runtime"
out=/tmp/optiscaler-build
mkdir -p "$out"
python3 Development/OptiScaler/prepare-host.py
x86_64-w64-mingw32-g++ -std=c++17 -O2 -shared -static -D_WIN32_WINNT=0x0A00 -DLMXXF_NR_RUNTIME_EXPORTS -I "$runtime" -I src -I Development/HIP "$runtime/LmxxfNrRuntime.cpp" -o "$out/LmxxfNrRuntime.dll" -ld3d12 -ldxgi -ld3dcompiler -ldxguid -luser32
x86_64-w64-mingw32-g++ -std=c++17 -O2 -static -municode "$host/tests/lmxxf_nr_gpu.cpp" -o "$out/runtime-smoke.exe" -ld3d12 -ldxgi -ldxguid
echo "Done: $out/LmxxfNrRuntime.dll"
