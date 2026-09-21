# C128 mapped all-zero tiles

The fused FFN/QKV has no bias terms. For the fixed finite model weights, a mapped input row outside the valid rectangle therefore produces canonical positive zero in both feature output and all3 normalized QKV parts. A uniform workgroup test may write those two complete output regions directly and return before shared memory or barriers. This does NOT skip the later attention computation.

Two probes, both using the original16-row/256-thread launch:

* `prepare.py`: checks rectangle intersection across at most two raster rows, handles wraparound; falls back when workw<16.
* `prepare.py --vertical`: only checks entire tiles above/below the valid rows using first+15 < sy*workw or first >= (sy+height)*workw. Conservative at partial tiles and ignores side-only padding. Avoids division and cross-row logic.

Both generators pin the pre-change source at79c1654, prepend production defines, and emit a complete module plus a reviewable patch. C128 mapped variants only; original valid-pixel arithmetic and other channel widths are unchanged. The controls cover mapped/unmapped f32 and byte paths through normal exports (no host ABI change).

`check-predicate.py` compares both tests to explicit16-row validity,1012 geometries including supported tiers/shifts and1000random small rectangles. It checks no false skip, including raster row wrap. GPU controls remain mandatory: run.ps1 or vertical-run.ps1 checks static/moving900/1080, -ExtraControls adds720/history/f32input/f32feature; -TimingFrames1000 enables longABBA. time-kernel.ps1 / vertical-time-kernel.ps1 uses the prior pure_c128_all.exe with its M32 routing disabled, changing only the module set, comparing raw full-network FP32 first/final results.

Build scripts guard games and compile gfx1200/gfx1201; runtime coverage is gfx1201. Match the candidate's documented module directory. collect.ps1 accepts -Experiment c128-empty-tile or c128-empty-vertical; analyze.py summarizes archived data. Test fixture references are the unchanged post-head-shared-input baseline. The native-game DLL does not require a host change for this kernel-only candidate.

Outcome: vertical-only patch adopted in main after dual-arch compile,96paired RGB controls,8raw FP32 checks and1000frame ABBA. Production source was checked byte-for-byte against the built candidate source (excluding build defines). General rectangle variant is not adopted. No game installation or release package was updated.
