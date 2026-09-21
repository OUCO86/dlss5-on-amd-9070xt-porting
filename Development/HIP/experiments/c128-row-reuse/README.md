# Step3: C128 expansion row reuse potential

Real block9 expansion weights512×128 (first65536 half values of block9-ffn.f16), synthetic finiteFP8 input26624×128 matching a900P shifted C128 grid's row count. export.py asserts weights are exactly representable in E4M3 and writes operands outside git. This is an isolated shape probe, NOT a full-network candidate.

Three kernels: M16×N64 baseline, M32×N64 sharing eachB fragment over twice as many rows, M32×N32 balancing reuse with fewer output columns. Same FP8 operands, original scalar activation form and per-output K order. run.ps1 builds both architectures, guards games and runs bench.exe. bench uses10000 warmups/20000 measured launches per slot, host wall/sync, ABBA candidate order1,2,2,1. Full output bytes checked against baseline after every slot. Initial shorter trial is archived separately.

M32×N64 saves~0.7–1.1%; balancedM32×N32 saves16.8–19.2% on this hot repeated operator. Balanced output tile contains the same1024 elements as baseline: global_load_b6440→32, WMMA32 unchanged, actualVGPR106→98, compilerOccupancy12 unchanged, scratch0. Do not extrapolate gameFPS or use the17–19% as whole-network gain. Fused-kernel integration requires phase-specific work partitioning and larger/changed LDS, which may erase it. Reports: results/c128-row-reuse-20260921.
