# C256 expansion wide B loads

prepare.py creates isolated /tmp/c256-wide-load/{src,Development/HIP,multihead_fast_padded.hip}. Host first packs normal fragments, then permutes each512-byte expansion-weight tile from [K16half][lane][8bytes] to [lane][K16half][8bytes]. Only C256 expansion changes; contraction/project/QKV regions retain original layout.

Kernel reads two contiguous B fragments using i4/memcpy16 and issues two original K16 FP8 MMAs, preserving each accumulator's K order. A still uses two8-byte reads. Matrix precision/shape/work unchanged. All C256 Frag exports in this experimental module require the corresponding experimental host: NEVER mix with ordinary DLL/weights. No game installation.

Build isolated Development/HIP/benchmark.cpp with normal MinGW HIP benchmark flags and isolated src include; output benchmark_c256_wide.exe. Upload to hip-backend; upload generated HIP source/build.ps1/run.ps1 to hip-backend/c256-wide-load. build.ps1 compiles both architectures, uses frozen post-head-shared-input-modules for unchanged modules. run.ps1 performs48 static/motion frame comparisons and160-frame ABBA; -TimingOnly -TimingFrames1000 runs longer repeats, dropping first200.

ISA gate passes: mapped C256 global_load_b64152→88 plus32 new global_load_b128, WMMA136 unchanged; next_free_vgpr101→97, LDS21568/private0 unchanged, compiler Occupancy12 and VGPRBlocks12 unchanged. Outputs exact on48 pairs.1080 saves~0.03ms in both short/long rounds;900 effectively tied. Retain as a small-gain candidate, not yet adopted in production. Before adoption add distinct wide-layout exports/options to prevent silent host/module mixing, and validate other input/geometry/history controls. Results in results/c256-wide-load-20260921.
