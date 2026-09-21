# Step2 result: higher C32 occupancy is slower here

Based on corrected compiler-resource interpretation, tested reducing LDS rather than blindly requesting fewerVGPRs. C32 post exact merged input staging costs4352bytes. Candidate recomputes/re-reads the same input at residual initialization, preserving rounding and all matrix operations.

Both targets compile,900/1080 frozen/1px motion ×12frames =48 RGB frame pairs bit-identical and finite. Shader metadata:
-Actual NumVgprs158→155.
-NumVGPRsForWavesPerEU / reserved217→169.
-LDS19712→15360bytes, compilerOccupancy6→8, scratch0.

160-frame ABBA, first32 excluded, normal clocks, no RGP/reuse/history:
-90013.221539→13.308988ms, +0.087449ms.
-108018.661582→18.785602ms, +0.124020ms.

Reject; no production/game update. Separate old no-unroll trials also lowered register use but regressed, so they were not blindly repeated. The result does not uniquely attribute time to registers/LDS/ALU/global loads; it tests this exact tradeoff. See kernel-bottleneck-20260921 for validated isolated counters and withdrawal of earlier mixed-API capture evidence.
