# C512 一头一 wave attention/projection 原型

`prepare.py` → /tmp/c512-wave：`kernel.hip`（multihead_fast_padded.hip + wave_owned_mh.inc 的辅助函数 + 本目录 `c512_attention.inc`，注意力核心从 wave_owned_mh.inc 拼接）和 `network.cpp`（当前生产 host 副本，W2Mode 0 生产 / 1 一头一 wave / 2 两 wave 一头 / 3 重复 attention / 4 重复 projection）。MinGW 编 host，`build.ps1 -Label x` 在 AMD 机编 gfx1201 模块（复制 wave-owned-production 的 24+2 模块），`run.ps1 -Heights 900 -Label x -Candidates 12` 跑 ABBA（`-Heights` 一次一档，数组经 -File 会被当成字符串）。结论与数据：`Development/results/c512-wave-20260926/README.md`（逐位通过、null，不采用）。
