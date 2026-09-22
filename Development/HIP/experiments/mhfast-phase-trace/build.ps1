$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\mhfast-phase-trace";$m="$d\modules"
& "$r\check-idle.ps1"
New-Item -ItemType Directory -Force $m|Out-Null
Copy-Item "$r\network-fixed-shapes\prod5-modules\*.hsaco" $m
& 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$m\multihead-fast-padded-wave-packed.hsaco" "$d\kernel.hip" comgr gfx1201
if($LASTEXITCODE){throw 'Compile failed'}
