$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\pdl-c512";$m="$d\modules"
& "$r\check-idle.ps1"
New-Item -ItemType Directory -Force $m|Out-Null
Copy-Item "$r\network-fixed-shapes\prod8-modules\*.hsaco" $m
foreach($name in 'deep_fast-packed','multihead-fast-padded-wave-packed','multihead_fused_attention','multihead-reference'){
 & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$m\$name.hsaco" "$d\$name.generated.hip" comgr gfx1201 | Out-Null
 if($LASTEXITCODE){throw "compile failed $name"}
 "$name "+(Get-FileHash "$m\$name.hsaco").Hash.Substring(0,16)
}
Select-String -Path "$m\*.hsaco.s" -Pattern '^\s+\.name:\s+\S+_pdl$' | ForEach-Object { $_.Line.Trim() } | Sort-Object -Unique | Measure-Object | ForEach-Object { "pdl kernels: $($_.Count)" }
'built'
