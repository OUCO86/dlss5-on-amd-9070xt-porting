$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\mh-phase-trace";$m="$d\modules"
& "$r\check-idle.ps1"
New-Item -ItemType Directory -Force $m|Out-Null
Copy-Item "$r\network-fixed-shapes\prod4-modules\*.hsaco" $m
& 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$m\multihead_fused_attention.hsaco" "$d\kernel.hip" comgr gfx1201
if($LASTEXITCODE){throw 'Compile failed'}
