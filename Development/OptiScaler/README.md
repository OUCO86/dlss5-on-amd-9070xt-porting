# OptiScaler pre-SR integration

Game scene colour → HIP neural rendering → FSR/DLSS → display. This integrates the lmxxf
HIP runtime into TheAutomatic's GPL-3.0 OptiScaler fork as a pre-SR backend.

Host dependency: https://github.com/TheAutomatic/dlss-5-amd-project, pinned commit
in `upstream.json`. The host modifications are preserved as patches; the lmxxf MIT
core remains separate.

## What this does

The OptiScaler host hooks DLSS/FSR dispatch and, before the upscaler runs, passes the
game's low-resolution frame to `LmxxfNrRuntime.dll` (the HIP runtime from this repo).
The neural result is then fed to the upscaler as usual. Because the integration lives
in the host layer, any game that works with OptiScaler works with the lmxxf backend —
no per-game hooking needed.

## Building

### Runtime (Linux, cross-compiled to Windows DLL)

```bash
bash Development/OptiScaler/build-runtime.sh
```

### Host (Windows, MSVC)

1. Clone the upstream repo to the path expected by `prepare-host.py`
   (default `/tmp/re9-upstream-bridge-review`).
2. Checkout the pinned commit from `upstream.json`.
3. Run `prepare-host.py` to apply patches and copy core headers/shaders.
4. Open the upstream solution in Visual Studio 2022 and build Release x64.

## Deploy

1. Copy the built OptiScaler host DLL next to the game exe.
2. Copy `LmxxfNrRuntime.dll` next to it.
3. Copy `native-game-tiled-assets/` (weights + HIP modules) next to it.
4. In `OptiScaler.ini`, set `[DlssNr] NrBackend=lmxxf`.
5. Run the game.

## Notes

- Standard 16:9 inputs (R10G10B10A2, R16G16B16A16, B8G8R8A8, etc.) work out of the box.
- RGB9E5 (HDR compressed) input requires `private_float_output` — see
  `src/native_game_codec.h`.
- Inputs larger than 1920×1080 are downsampled by the codec when `DLSS5_FIT_LARGE=1`.
