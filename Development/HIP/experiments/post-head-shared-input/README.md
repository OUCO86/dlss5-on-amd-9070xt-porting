# Post/head RGB feature reuse

Candidate assigns one of16 active lanes per token and computes its three RGB dot products together, loading each shared feature once. Per-color32-term multiplication/addition and final rounding remain in original order. Other C32 paths unchanged. Replaces48 color-tasks across32 lanes, trading active lanes for shared inputs and independent accumulators.

prepare.py generates source/patch from frozen main commit e151f8b into /tmp/post-head-shared-input; safe to reproduce after adoption. Upload source and build.ps1/run.ps1 to D:/DLSSNR-Lab/hip-backend/post-head-shared-input. build.ps1 builds gfx1200/gfx1201 and assembles a candidate module set against frozen main-reuse-modules. run.ps1 checks48 paired static/motion RGB outputs and two resolution ABBA timings; -TimingOnly repeats timing with separate tags.

Both timing rounds positive by0.010–0.028ms across900/1080; exact48 frame pairs. Small measured saving, no game-FPS promise or formal confidence interval. Adopted in main source; games and released0.27 ZIPs remain unchanged. See results/post-head-shared-input-20260921.
