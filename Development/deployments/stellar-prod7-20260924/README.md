# prod7 候选：prod6 + mh_fast 全行写（HIP_FFN_LINE_STORES=1）

只换 mh_fast 模块（两架构）。依据 `results/mhfast-line-stores-20260924`（逐位，−0.6/−0.7%；FFN 占满时钟 +1.2%）。
流程同 prod6：`build.ps1`（fence-prod7\mhfast.generated.hip → prod7-modules / prod7-gfx1200）→ `regression-prod7.ps1 -TimingFrames 1000` 与 `-ExtraControls`（对 prod2 逐位基线）→ `payload.json` → `install.ps1`（剑星关闭时；`-RestoreBackup <dir>` 回滚）。
