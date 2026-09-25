$ErrorActionPreference='Stop'
$r='D:\DLSSNR-Lab\hip-backend';$d=Split-Path -Parent $MyInvocation.MyCommand.Path
& "$r\check-idle.ps1"
$m="$d\modules";New-Item -ItemType Directory -Force $m | Out-Null
Copy-Item "$r\network-fixed-shapes\prod8-modules\*.hsaco" $m
& 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$m\c64-wave2.hsaco" "$d\kernel.hip" comgr gfx1201
if($LASTEXITCODE){throw 'Compile failed'}
Get-FileHash "$m\c64-wave2.hsaco"
