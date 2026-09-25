#!/usr/bin/env bash
# Build LmxxfNrRuntime.dll for generic OptiScaler host.
# Run after prepare-host.py.
set -euo pipefail
cd "$(dirname "$0")/../../.."
host="${HOST_DIR:-/tmp/optiscaler-generic-host}"
runtime="$host/OptiScaler-DLSSNR-PreSR-Multipass-main/OptiScaler/dlssnr/backend/lmxxf_runtime"

python3 Development/OptiScaler/prepare-host.py

mkdir -p /tmp/optiscaler-runtime-build
x86_64-w64-mingw32-g++ -std=c++17 -O2 -shared -static \
  -D_WIN32_WINNT=0x0A00 -DLMXXF_NR_RUNTIME_EXPORTS \
  -I "$runtime" -I src -I Development/HIP \
  "$runtime/LmxxfNrRuntime.cpp" \
  -o /tmp/optiscaler-runtime-build/LmxxfNrRuntime.dll \
  -ld3d12 -ldxgi -ld3dcompiler -ldxguid

echo "Built /tmp/optiscaler-runtime-build/LmxxfNrRuntime.dll"
