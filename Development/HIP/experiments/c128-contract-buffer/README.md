# C128 separate contraction output

Only C128: adds16*(128+4)=2112 bytes of declared shared storage for contraction output and removes the barrier before overwriting expansion inputs. Projection consumes the new buffer. The post-write barrier remains. Arithmetic and other channel routes unchanged. No additional kernel launch.

prepare.py emits /tmp/c128-contract-buffer source and candidate.patch, leaving production untouched. Upload source/build.ps1/run.ps1 to D:/DLSSNR-Lab/hip-backend/c128-contract-buffer. Build both architectures, then run game-guarded48 frame comparisons and900/1080 ABBA against post-head-shared-input-modules. Result: no gain, candidate not adopted. See results/c128-contract-buffer-20260921.
