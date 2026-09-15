# C32 caching and32-row MH tiles (2026-09-15)

Archived patch against e847b44; experiments were removed from the default code
because they did not show a stable whole-network improvement. The patch
preserves the implementation for a future isolated checkout. It adds:

- HIP_C32_CACHE_QKV: retain two FP8 FFN operand fragments across C32 Q/K/V.
- --mh-tile32:32×64 output tiles using256 threads instead of64×64/512.
- --mh-tile32-kernel NAME: apply the smaller tile to one exact kernel name.
- HIP_C32_SCALE_CACHE with HIP_PREPACKED_WEIGHTS: consume three scale components
  appended by the patched host at float offset8736 (96 extra floats).

All tested normal900 outputs matched7b959143… exactly. ABBA, four processes,
six iterations each, exclude cold; ten hot samples per variant. Medians in ms:

| Experiment | Baseline | Candidate |
|---|---:|---:|
| C32 QKV input cache |45.2550|45.2555|
| All MH32-row tiles |45.5680|46.1290|
| QKV+norm only |45.4285|45.5270|
| FFN expand only |45.3370|45.7280|
| FFN contract only |45.4835|46.1310|
| FFN project only |45.4655|45.4760|
| Attention matrix projection only |45.5340|45.3835|
| C32 scale components |45.2945|45.3460|

The small attention-projection difference is not treated as a stable gain.
Logs are in ignored release/HIP/c32-cache-test.log, tile32-test.log,
tile32-k0.log through tile32-k4.log, and scale-test.log. Remote experimental
module sets are c32-cache-modules, tile32-modules and scale-modules under
D:/DLSSNR-Lab/hip-backend. No experimental module was installed in the game.
