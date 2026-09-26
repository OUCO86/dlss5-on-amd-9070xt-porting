$ErrorActionPreference='Stop'
$r='D:\DLSSNR-Lab\hip-backend';$d=Split-Path -Parent $MyInvocation.MyCommand.Path
& "$r\check-idle.ps1"
$m="$d\modules";New-Item -ItemType Directory -Force $m | Out-Null
Copy-Item "$r\vit-proj-n64-production\modules-gfx1201\*.hsaco" $m
$orig=(Get-FileHash "$m\c32-wave1.hsaco").Hash;Copy-Item "$m\c32-wave1.hsaco" "$d\c32-wave1.production.hsaco" -Force
& 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$m\c32-wave1.hsaco" "$d\kernel.hip" comgr gfx1201
if($LASTEXITCODE){throw 'Compile failed'}
"production c32-wave1 $orig";"instrumented c32-wave1 $((Get-FileHash "$m\c32-wave1.hsaco").Hash)"
