# Current-network timing localization with validated output controls

Snapshot: main6fd3390, with the C128/C256 exact-zero shortcuts. Modules are the validated mh-empty-c256-modules set. Graph/adaptive reuse/history are disabled. A frozen1296×720 HDR capture is encoded normally at900/1080; the encoded input and raw expected output are then uploaded once into a standalone pureHIP process, post_shift3. No game deployment or GPU clock-setting APIs.

## Rejected dense timing

`prepare.py` creates a temporary host with preallocated begin/end HIP events around all234Run dispatches, plus frame boundaries. Stage names/scalar arguments are recorded for topology. `run.ps1` first captures the exact encoded input/output using dump.exe (normal mixed-API execution without a profiler), checks the existing RGB goldens, then runs pure.exe.

Six raw output checks per tier pass, and event ordering is valid, but per-dispatch events inflate~12.8→23.4ms at900 and~18.2→28.8ms at1080. Dense timeline.csv is retained for **topology only**, not a real cost breakdown. Functional correctness and monotonic timestamps alone do not establish non-invasive profiling.

## Accepted sparse-prefix method

`prepare-prefix.py` copies the clean production host (not the dense-instrumented copy). Each timed frame has one interior timestamp at a chosen dispatch cut, plus start/end markers. The end marker is after the last compute dispatch, before the final device-output copy. Cut0 and234 reuse the start/end event handles instead of measuring an empty interval. Every frame gets a unique preallocated event triplet, and timestamp readiness is checked explicitly. Run dispatch count must remain234; a changed topology aborts.

The earlier version reused three handles and measured very short/empty intervals, occasionally yielding negative times. It was rejected. Unique handles, shared endpoint events and stopping at the compute boundary passed the final checks; this does not establish the driver's internal reason for the earlier failures.

15contiguous regions cover all compute dispatches. For each region, measure its left/right prefix boundaries in8localABBA rounds (32frames); difference of the mean right and left prefix is the region estimate. No actual kernel is omitted or duplicated. There are480timed frames per tier, plus warmup and unmarked before/after controls.17full rawFP32 output checks per tier pass. The two tiers' sparse marked wall medians remain close to normal; reconstructed region sums agree with independently measured compute spans within~0.4%/1.0%.

`run-prefix.ps1` uses the captured inputs from the first run. Compile emitted /tmp/network-prefix/pure.cpp as prefix.exe; compile /tmp/network-timeline/pure.cpp as pure.exe. Both use MinGW -std=c++17 -O2 -static -D_WIN32_WINNT=0x0A00. dump.cpp additionally needs -municode, -DNATIVE_GAME_TILED_VERIFICATION, -DDLSS5_USE_HIP, -DDLSS5_BENCH_BRIDGE_ISOLATE, -I<repo>/src and -ld3d12 -ldxgi -ld3dcompiler -ldxguid. All scripts use the existing Windows lab and guard known games/Magpie.

`collect.ps1` saves smallCSV/logs/flags and hashes (large capturedF32 buffers remain in the lab). `analyze.py` validates all timing arithmetic/topology and computes region/family results. Individual ABBA differences may be negative for tiny transition regions because they subtract different frames; they are not clipped. Such small regions should not be finely ranked.

## What the tables mean

These are region times, including data movement, intra-region launch/queue behavior and all arithmetic, not pure ALU busy cycles. Families include adjacent down/up transitions; C32's11dispatches include one upsampling dispatch. The approximate principal-matrix work estimate reuses the documented analytic model and subtracts the now-skipped C128/C256 zero tiles. It omits conversion, activation, normalization, simulated diagonal/reduction work and some transition accounting; its TFLOPS ratio is not hardware utilization.

`audit-c32.ps1` verifies the assembly artifact's siblingHSACO matches the timed C32 module SHA256 before `audit-c32.py` counts static instruction classes. No static count is interpreted as an executed count, elapsed-time share or dual-issue eligibility ratio. Results and limitations are in Development/results/network-timeline-20260921/report.md.
