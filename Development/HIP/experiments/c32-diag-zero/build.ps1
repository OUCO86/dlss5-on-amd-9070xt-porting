$ErrorActionPreference='Stop'
$r='D:\DLSSNR-Lab\hip-backend'
$d=Split-Path -Parent $MyInvocation.MyCommand.Path
& "$r\check-idle.ps1"
$baseline="$r\network-fixed-shapes\prod8-modules"
if(!(Test-Path "$baseline\c32_fused_ffn_attention-packed.hsaco")){throw 'prod8 modules missing'}
$m="$d\modules"
New-Item -ItemType Directory -Force $m | Out-Null
Copy-Item "$baseline\*.hsaco" $m
Get-ChildItem "$baseline\*.hsaco" | Get-FileHash | Export-Csv "$d\baseline-hashes.csv" -NoTypeInformation
& 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$m\c32_fused_ffn_attention-packed.hsaco" "$d\kernel.hip" comgr gfx1201
if($LASTEXITCODE){throw 'Compile failed'}
Get-FileHash "$m\c32_fused_ffn_attention-packed.hsaco"
