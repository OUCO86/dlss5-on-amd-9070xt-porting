$ErrorActionPreference='Stop'
$r='D:\DLSSNR-Lab\hip-backend';$d=Split-Path -Parent $MyInvocation.MyCommand.Path
& "$r\check-idle.ps1"
$m="$d\candidate-modules";New-Item -ItemType Directory -Force $m | Out-Null
Copy-Item "$r\network-fixed-shapes\prod8-modules\*.hsaco" $m
foreach($arch in 'gfx1201','gfx1200'){
 $dest=if($arch -eq 'gfx1201'){$m}else{"$d\candidate-gfx1200"}
 New-Item -ItemType Directory -Force $dest | Out-Null
 & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$dest\c32_fused_ffn_attention-packed.hsaco" "$d\candidate.hip" comgr $arch
 if($LASTEXITCODE){throw "Compile failed $arch"}
 Get-FileHash "$dest\c32_fused_ffn_attention-packed.hsaco"
}
