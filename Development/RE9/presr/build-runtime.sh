#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../../.."
host=/tmp/re9-upstream-bridge-review
runtime="$host/OptiScaler-DLSSNR-PreSR-Multipass-main/OptiScaler/dlssnr/backend/lmxxf_runtime"
mkdir -p /tmp/re9-presr-build
python3 Development/RE9/presr/prepare-host.py
x86_64-w64-mingw32-g++ -std=c++17 -O2 -shared -static -D_WIN32_WINNT=0x0A00 -DLMXXF_NR_RUNTIME_EXPORTS -I "$runtime" -I src -I Development/HIP "$runtime/LmxxfNrRuntime.cpp" -o /tmp/re9-presr-build/LmxxfNrRuntime.dll -ld3d12 -ldxgi -ld3dcompiler -ldxguid
x86_64-w64-mingw32-g++ -std=c++17 -O2 -static "$host/tests/lmxxf_nr_gpu.cpp" -o /tmp/re9-presr-build/runtime-smoke.exe -ld3d12 -ldxgi -ldxguid
