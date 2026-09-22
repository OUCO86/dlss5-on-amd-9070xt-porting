#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="${1:-bin}"
mkdir -p "$OUT"
CXX="${LMXXF_GXX:-x86_64-w64-mingw32-g++}"
"$CXX" -std=c++17 -O2 -shared -static -static-libgcc -static-libstdc++ -D_WIN32_WINNT=0x0A00 -DLMXXF_NR_RUNTIME_EXPORTS -I include -I src -I Development/HIP src/LmxxfNrRuntime.cpp -o "$OUT/LmxxfNrRuntime.dll" -Wl,--out-implib,"$OUT/LmxxfNrRuntime.dll.a" -ld3d12 -ldxgi -ld3dcompiler -ldxguid
echo "BUILD_OK $OUT/LmxxfNrRuntime.dll"
