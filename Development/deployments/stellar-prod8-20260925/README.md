# prod8 候选：prod7 + 链上 launch 任意序 + tile 旗子（土法 PDL）

依据 `results/pdl-chain-20260925`（逐位；900 −1.6%、1080 −0.6%）。改动三处：`hip/multihead_fast_padded.hip` 与 `hip/multihead_fused_attention.hip` 各加 helper 与 `_pdl` 孪生（宏 `HIP_PDL_KERNELS`，原核代码不动，模块哈希变）；`Development/HIP/hip_reference_network.h` 的 `opt.pdl`（`DLSS5_HIP_PDL=1`，默认关）；插件 `dlss5-amd.addon64` 重编（含同一 host）。
流程：`build.ps1`（prod8\mhfast/mhfused.generated.hip → prod8-modules / prod8-gfx1200，两架构各两模块）→ `regression-prod8.ps1 -TimingFrames 1000`（runner `benchmark_main_reuse_pdl.exe` 新 host；候选 = prod8 模块 + `DLSS5_HIP_PDL=1`，基线 = prod2 模块 + `=0`，12 帧哈希逐位 + 1000 帧 ABBA）→ `payload.json`（4 模块 + 插件）→ `install.ps1`（剑星关闭时；写 `DLSS5_HIP_PDL=1` 进 flags；`-RestoreBackup <dir>` 回滚含 flags）。
