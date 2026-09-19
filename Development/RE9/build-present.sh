#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
b=$(mktemp -d)
trap 'rm -rf "$b"' EXIT
ln -s /usr/x86_64-w64-mingw32/include/windows.h "$b/Windows.h"
x86_64-w64-mingw32-g++ -std=c++17 -O2 -shared -static -Wno-attributes -D_WIN32_WINNT=0x0A00 -DNATIVE_GAME_TILED_VERIFICATION -DDLSS5_USE_HIP -DDLSS5_RE9_POST_1440 -I"$b" -Ithird_party/reshade/include Development/RE9/present_addon.cpp -o "${1:-/tmp/re9-present.addon64}" -ld3d12 -ldxgi -ld3dcompiler -ldxguid
