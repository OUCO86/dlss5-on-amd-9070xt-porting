# C128 QKV input fragment reuse inside fused FFN

Only C128 non-BatchNorm path: preload eight i2 input fragments, share them across Q/K/V rather than reload qfeature each time. Matrix operands/accumulation/normalization orders unchanged. Other channel counts use original loads. prepare.py generates a temporary HIP source and patch; production unchanged.

Upload generated /tmp/c128-qkv-input-reuse/multihead_fast_padded.hip plus build.ps1/run.ps1 to D:/DLSSNR-Lab/hip-backend/c128-qkv-input-reuse. Both targets compile with HIP_ISA_HALF/HIP_PREPACKED_WEIGHTS/HIP_FFN_HOIST_RES2. Frozen post-head-shared-input-modules (including adopted RGB change) is the baseline. run.ps1 performs game guards,48 frame comparisons and900/1080 ABBA; TimingOnly is available but was unnecessary after negligible first-round results.

No gain; candidate not adopted. See results/c128-qkv-input-reuse-20260921/report.md.
