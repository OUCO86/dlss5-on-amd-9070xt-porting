$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\c32-transposed-tail";$m="$d\modules"
& "$r\check-idle.ps1"
New-Item -ItemType Directory -Force $m|Out-Null
Copy-Item "$r\network-fixed-shapes\prod6-modules\*.hsaco" $m
Copy-Item "$r\c32-lds-alias\network.exe" $d -Force
# 1. production body unchanged: prod.hip (flag 0) must match prod6 ISA apart from __hip_cuid_
& 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$d\prod-check.hsaco" "$d\prod.hip" comgr gfx1201
if($LASTEXITCODE){throw 'prod compile failed'}
$a=(Get-Content "$d\prod-check.hsaco.s") -replace '__hip_cuid_[0-9a-f]+','__hip_cuid_'
$b=(Get-Content "$r\network-fixed-shapes\prod6-modules\c32_fused_ffn_attention-packed.hsaco.s") -replace '__hip_cuid_[0-9a-f]+','__hip_cuid_'
$diff=Compare-Object $a $b
"prod ISA diff lines: $($diff.Count)"
# 2. ABBA module (production + three transposed twins), both architectures
foreach($arch in 'gfx1200','gfx1201'){
 $file=if($arch -eq 'gfx1201'){"$m\c32_fused_ffn_attention-packed.hsaco"}else{"$d\gfx1200.hsaco"}
 & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' $file "$d\kernel.hip" comgr $arch
 if($LASTEXITCODE){throw "compile failed $arch"}
}
Select-String -Path "$m\c32_fused_ffn_attention-packed.hsaco.s" -Pattern '^\s+\.vgpr_count:|^\s+\.sgpr_count:|^\s+\.name:|\.group_segment_fixed_size:' | ForEach-Object { $_.Line.Trim() } | Select-Object -First 400 > "$d\meta.txt"
'built'
