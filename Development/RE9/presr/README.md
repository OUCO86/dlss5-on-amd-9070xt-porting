# RE9 pre-SR integration experiment

Goal: game scene colour → HIP neural rendering → FSR → display. This is an experimental host integration, not a published package.

Host dependency: TheAutomatic's GPL-3.0 OptiScaler fork, release/1.9.0 commit `8f71f73bfc836a37936e7cee6701750ad4e8bfec` from https://github.com/TheAutomatic/dlss-5-amd-project. His submission-splitting design and PR https://github.com/lmxxf/dlss5-on-amd-9070xt-porting/pull/5 motivated this integration. PR #5 was not merged. Our MIT bridge implementation is separate; host modifications are preserved as patches, retaining upstream licensing.

`prepare-host.py` uses the pinned checkout at `/tmp/re9-upstream-bridge-review`, applies adaptations and copies current core headers/shaders. Windows build uses `build-host.ps1`; MSVC v143 and Windows SDK 26100 are installed under `D:\DLSSNR-Lab\build-tools`. The host lives under `D:\DLSSNR-Lab\re9-presr\source`; builds go to `bin`. Upstream packaging/install events are disabled. Dependencies: xess 8fe81bdbbaf00b3c1b733fd0d830c333dc84e6f0; FidelityFX-SDK c6efa6bf7f2027b3ec94f28578bb5965eabb9e55; FidelityFX-SDK-v2 60f4ea81909200d8542eca14dccb2628b763a9a3.

`install.ps1` refuses a running RE9 process, backs up all touched files with an existence manifest, installs host/runtime in root and `_storage_`, disables the old post-present addon, and selects 2560×1440 borderless / DLSS Balanced / frame generation off. `-RestoreBackup <directory>` restores that installation transaction. Original pre-experiment backup: `D:\DLSSNR-Lab\re9-presr\backups\20260922-064814-585`.

Observed RE9 input is 1506×848 RGB9E5 (DXGI 67), not a 2K allocation. Codec opt-in private FP16 output permits that SRV format without changing generic addon raw-copy format support. The consumer can be prerecorded, but actual GPU submission remains producer → HIP enqueue/wait → consumer → acknowledgement.

Completed checks so far:
- Core bridge prerecord tests on gfx1201: 900/1080 and legacy Graph reference pass.
- Host compilation; command-list split, Create/Execute hooks, CL1 wrapping and same-frame boundary harnesses pass. The latter includes real overlapping placed textures, alias switches, current-frame byte comparisons, 16 split submissions/replays, state restoration and failed Reset.
- RE9 split-original control initially rejected every frame due to aliasing. Alias barriers now remain verbatim in their segment; a completed alias barrier does not invalidate a later cut. Cuts during unfinished transitions remain rejected. Real RE9 split submissions then succeed with FSR result 0.
- Runtime RGB9E5 1506×848 smoke: PrepareFrame/HIP/consumer acknowledgement/GPU completion/destruction succeed. This smoke does not establish image quality.

Aliasing semantics reference: https://learn.microsoft.com/en-us/windows/win32/direct3d12/using-resource-barriers-to-synchronize-resource-states-in-direct3d-12 . A same-queue cut preserves the ordering of the actual alias barrier; do not replay it on the continuation or treat it as a resource-state transition.

Full NR candidate installed and started successfully: 1506×848 scene input, 1600×900 network, 2560×1440 borderless output. First five evaluations show successful HIP enqueue, producer/continuation submission, zero skips and zero submission failures. Main menu screenshot renders normally; process remained live for over two minutes without a neural failure status. Real gameplay, motion quality and frame generation remain user validation. The old post-present addon is disabled, so there is no duplicate neural pass. Candidate hashes and game log are under `results/`. The game is left running at the main menu for testing.
