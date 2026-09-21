# C32 output-preserving phase repetition probes

This batch is stored phase-by-phase; it is **not** a native-time-share decomposition or a cross-phase optimization ranking. Base source is pinned tocd54a28. No production kernel, game DLL, configuration or package is modified.

`prepare.py` keeps the original C32 exports and appends seven instrumented body variants, each exported for input-prefix, first raw chain, and post/RGB. Repetition count1/2/4 is encoded in the high nibble of the diagnostic export's windows argument and decoded before its bounds check; real windows remain below2^28. Ordinary exports never receive this encoding. Grid/thread geometry and all other arguments are unchanged. This private diagnostic ABI avoids any production host/kernel interface change.

Phases:

* ffn: expansion dots, contraction dots and original residual initialization. Activation/format output is performed once.
* pack: FFN activation and RTZ/FP8 arithmetic, observed scalar-by-scalar. Repeated stores may sink; this is not a repeated-LDS-traffic test. This version has substantial calibration overhead.
* qkv: QKV dots, normalization after repeated dots. The FFN/V storage alias is respected.
* scores: Q×K dots, bias and half exponent encoding. Probability packing happens afterward.
* norm: Q/K normalization and QKV packing, then probability normalization/packing. Requires production non-aliasing probability scratch layout. The outer three-part QKV loop is explicitly unrolled to retain the original structure.
* av: AV dots only; packed AV is published once afterward.
* project: final attention projection, residual/RTZ and output staging. Finish/downsample/RGB epilogues run once.

`prepare-packv.py` adds a separate encoding probe using one opaque-register boundary for a whole fragment rather than one boundary per scalar. It measures the same arithmetic family while preserving more scheduling freedom. It is a calibration experiment, not a production optimization. packv still perturbs the kernel, especially prefix/post. Original and intermediate calibration records are retained under initial-900-post and unroll-control-900-post.

Each target/phase runs three localABBA comparisons: original vs probe1, probe1 vs probe2, probe1 vs probe4. Warmup/pilot adapt measured batches toward200ms; host wall/sync is used, with no per-kernel GPU timing events. Every produced buffer is compared byte-for-byte after every slot: prefix main8+down, chain half output, or post floatRGB. Full raw network output is checked on both replay frames. Kernel references are real current-network tensors, not synthetic data.

900/1080 ×prefix/chain/post gives six cases. The final main batch has504slots; packv adds72. All576slots and24raw network comparisons pass. Both diagnostic modules compile for gfx1200/gfx1201; execution is gfx1201 only. FixedHDR capture, seed0, no history, Graph/adaptive reuse off. Inputs/expected outputs are the independently validated network-timeline captures.

Build the generated pure.cpp with MinGW -std=c++17 -O2 -static -D_WIN32_WINNT=0x0A00. Build main and packv modules with build.ps1/build-packv.ps1. Main uses pure.exe/modules; packv uses pure-filter.exe/modules-packv and DLSS5_C32_PROBE_PHASE=packv. Never install these modules in a game. All GPU scripts guard known games/Magpie. `run.ps1` defaults to the six main cases; `run-packv.ps1` to the six supplemental cases. `collect.ps1` and `analyze.py` archive/validate smallCSV/logs/hashes.

The N=1 calibration must accompany every marginal number. Runtime loops/opaque observations change scheduling and sometimes resources even when output is exact. Repeating a phase in a hot loop changes cache/power/dependency behavior; (T2−T1) and (T4−T1)/3 are controlled increments, not necessarily native phase durations and must not be added into a whole-kernel percentage. Reports remain separate in Development/results/c32-phase-cost-20260921/reports/ pending the later overall investigation summary.
