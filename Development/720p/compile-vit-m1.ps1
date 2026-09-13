$ErrorActionPreference='Stop'
Set-Location 'D:\DLSSNR-Lab\network-720p\DLSS5-AMD\native-game-tiled-assets'
$dxc='D:\DLSSNR-Lab\matrix-probe\dxc-preview\bin\x64\dxc.exe'
$inc='D:\DLSSNR-Lab\matrix-probe\dxc-preview\inc\hlsl'
& $dxc -I $inc -T cs_6_10 -E expand -HV 2021 -enable-16bit-types -O3 -D VIT_EXPAND=1 -D BLOCK_N=4 -D BLOCK_M=1 -D NATIVE_FAST_ACCUMULATE=1 -D NATIVE_FAST_EPILOGUE=1 -D NATIVE_FP8_OPERANDS=1 -D NATIVE_FP8_HIDDEN=1 -D NATIVE_PACKED_INPUT=1 -D NATIVE_VIT_TILED=1 native_wave_vit_blocked.hlsl -Fo native_wave_vit_expand_packed.cso
exit $LASTEXITCODE
