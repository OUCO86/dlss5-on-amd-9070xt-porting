# modules-cand = production gfx1201 set + cvi-vec / cvi-vecsplit / cvi-split (c32-wave1 recipe + macros)
$ErrorActionPreference='Stop'
$r='D:\DLSSNR-Lab\hip-backend';$d=Split-Path -Parent $MyInvocation.MyCommand.Path
$m="$d\modules-cand";New-Item -ItemType Directory -Force $m | Out-Null
Copy-Item "$r\vit-proj-n64-production\modules-gfx1201\*.hsaco" $m
foreach($n in 'cvi-vec','cvi-vecsplit','cvi-split'){
 & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$m\$n.hsaco" "$d\$n.hip" comgr gfx1201
 if($LASTEXITCODE){throw "Compile failed $n"}
 "$n $((Get-FileHash "$m\$n.hsaco").Hash)"
}
