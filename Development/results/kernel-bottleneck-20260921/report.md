# Step1: isolate kernel memory counters with output validation

Mixed D3D12/HIP RGP capture FAILED output validation: targeted repeated-C32 finaldb7fa2b1…; earlier whole-pipeline captured final6a933465…; ordinary reference75aaba5e…. Frames also changed despite restored frozen input. No-RGP control and no-RGP10000x repeated C32 both match reference. Specific cause within mixed capture/interop remains unresolved; do not call this a proven game defect or a proven driver defect. Earlier whole-capture21.7% stalled is withdrawn as evidence of normal inference. Ordinary non-RGP performance comparisons remain valid.

Replacement: dump encoded real input/raw expected network output outside profiling; create the same HIP Options without creating a D3D12 context. post_shift3 matches NativeGameFrame (initial0 was caught by the pure-control check and corrected). Same input uploaded once. Target's first call repeats10000 times; RDP captures16 dispatches starting3000 within that region. Normal launch index logged below3000, and no other explicit HIP calls are inserted inside the repeated loop. Program remains alive2000 network frames for trace processing. All3 captures' first/final raw FP32 network outputs match expected exactly.

| Isolated target | Memory unit busy | Memory unit stalled | L0 hit | L2 hit | LDS bank conflict |
|---|---:|---:|---:|---:|---:|
| C32 post/head |99.056%|5.461%|71.619%|96.188%|0%|
| C128 mapped fused FFN/QKV bytein |93.021%|49.480%|80.988%|98.086%|2.062%|
| C256 mapped fragment fused FFN/QKV bytein |76.498%|15.560%|40.300%|99.201%|1.585%|

Counters are denominator-weighted provider ratios, validated sample-by-sample by read-counters.py. This is repeated-kernel hot-cache profiling at profiler clocks, not ordinary full-network attribution. Captures are16 repeated dispatches each, not complete frames; fewer samples for short FFNs. High cache hit is not equivalent to low memory-unit backpressure. C128 is the strongest memory-stall lead among these targets; C32's high memory busy does not itself prove stalled fetches. These counters do not distinguish all execution/dependency/barrier wait categories; dynamic instruction timing is still needed for that.

Raw traces remain hip-backend/kernel-bottleneck-pure-results/{case}/trace.rgp, local/tmp/{case}.rgp. Parsed counters/hashes and concise capture logs retained here; trace binaries not committed. Game/production code untouched.

Step2 resource correction: C32 post/head actual NumVgprs158, NumVGPRsForWavesPerEU217, LDS19712, compiler Occupancy6, private0. Earlier217 was a reservation/occupancy field, not actual live register count. Unfused post actual153 but stillOccupancy6. Reducing actual registers alone need not increase occupancy; LDS is also a bound. Historical no-unroll reduced registers but regressed; do not blindly repeat it.
