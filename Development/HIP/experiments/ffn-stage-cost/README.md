# Diagnostic stage duplication

prepare.py generates four independent HIP modules under/tmp/ffn-stage-cost. build.ps1 compiles gfx1201 diagnostic modules and combines them with frozen post-head-shared-input-modules. run.ps1 guards game processes, performs900P160-frame ABBA per stage, checks finite frame stats and matching final output hashes. These modules repeat work and must never ship. Results: Development/results/ffn-stage-cost-20260921. Empty asm inhibits removal of duplicate work; measurements include altered compiler/resource behavior and are not an additive decomposition.
