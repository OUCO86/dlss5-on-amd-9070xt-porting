# Lossless single-pack probe

prepare.py generates /tmp/c32-single-pack/c32_fused_ffn_attention.hip and candidate.patch without modifying production. Build check.cpp with MinGW C++17/static and -IDevelopment/HIP. Upload generated source/build.ps1/check_single_pack.exe/run.ps1 to D:/DLSSNR-Lab/hip-backend/c32-single-pack. Build both architectures; run.ps1 checks no games are running, enumerates65536 half encodings, verifies48 paired frame hashes and runs900/1080 whole-network ABBA against main-reuse-modules.

Zero semantic mismatches, but no meaningful speedup. Candidate not adopted. See results/c32-single-pack-20260921/report.md. Do not rerun blindly: the older non-prefetch single-cast trial also had only tiny gains.
