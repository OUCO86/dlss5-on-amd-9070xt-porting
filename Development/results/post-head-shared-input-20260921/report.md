# Post/head shared RGB input — 2026-09-21

One lossless change to the RgbHead epilogue of c32_fused_body. Original48 RGB tasks per16-token wave reread each feature for three color channels. Candidate uses16 lanes, one per token, loads a feature once and updates three independent scalar accumulators. Each channel's sequential32-term sum, Hrtz and final color/clamp arithmetic remain unchanged. No weight/skip/reuse policy change.

Both gfx1200/gfx1201 compile.900/1080 × static/1px horizontal motion ×12frames =48 paired RGB hashes identical; all recorded frames finite. Same1296×720 HDR capture and controlled transformation, not independent gameplay scenes or temporal-history validation. Arithmetic layout is the same for each color despite changed task assignment.

Clean160-frame host-wall ABBA, discard first32, reuse/history off, no diagnostic RGB writes during timing:

| Round |900P baseline→candidate|1080P baseline→candidate|
|---|---|---|
| Initial |13.170375→13.146500ms (−0.023875)|18.668758→18.655883ms (−0.012875)|
| Repeat |13.205371→13.195055ms (−0.010316)|18.734285→18.705926ms (−0.028359)|

All16 per-frame timing CSVs retained. All four comparisons positive, but magnitudes are small and comparable to some endpoint drift. Treat as a modest repeat-observed improvement, not proof of a fixed speedup on all systems or visible FPS uplift. Repeated timing was justified by the small initial result; no further sweeps performed.

Adopted simple source change, no config/API changes. Other C32 paths are unchanged. Main source is updated; installed game modules and existing0.27 packages are not. Next build/package must compile the updated C32 module rather than reuse the old0.27 C32 artifact. Candidate artifacts remain under D:/DLSSNR-Lab/hip-backend/post-head-shared-input and post-head-shared-input-modules.
