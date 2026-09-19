#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
b=$(mktemp -d)
trap 'rm -rf "$b"' EXIT
ln -s /usr/x86_64-w64-mingw32/include/windows.h "$b/Windows.h"
for unit in hook trampoline buffer hde/hde64; do
 x86_64-w64-mingw32-gcc -O2 -Ithird_party/minhook/include -Ithird_party/minhook/src -c "third_party/minhook/src/$unit.c" -o "$b/${unit##*/}.o"
done
x86_64-w64-mingw32-g++ -std=c++17 -O2 -shared -static -Wno-attributes -D_WIN32_WINNT=0x0A00 -DNATIVE_GAME_TILED_VERIFICATION -DDLSS5_USE_HIP -I"$b" -Ithird_party/reshade/include -Ithird_party/minhook/include Development/RE9/present_addon.cpp "$b"/*.o -o "${1:-/tmp/re9-present.addon64}" -ld3d12 -ldxgi -ld3dcompiler -ldxguid
