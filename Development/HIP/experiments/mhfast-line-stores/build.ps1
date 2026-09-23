$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\mhfast-line-stores";$m="$d\modules"
& "$r\check-idle.ps1"
New-Item -ItemType Directory -Force $m|Out-Null
Copy-Item "$r\network-fixed-shapes\prod6-modules\*.hsaco" $m
Copy-Item "$r\fence-scope-all\network.exe" "$d\network.exe"
foreach($pm in 1,2,3){
 $dest="$m\pair$pm";New-Item -ItemType Directory -Force $dest|Out-Null
 foreach($name in 'c32_fused_ffn_attention-packed','multihead_fused_attention','deep_fast-packed'){Copy-Item "$m\$name.hsaco" "$dest\$name.hsaco"}
 & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$dest\multihead-fast-padded-wave-packed.hsaco" "$d\pair$pm\multihead-fast-padded-wave-packed.generated.hip" comgr gfx1201
 if($LASTEXITCODE){throw "Compile failed $pm"}
}
& 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$d\prod-check.hsaco" "$d\prod.hip" comgr gfx1201
$a=(Get-Content "$d\prod-check.hsaco.s") -replace '__hip_cuid_[0-9a-f]+','__hip_cuid_'
$b=(Get-Content "$r\network-fixed-shapes\prod6-modules\multihead-fast-padded-wave-packed.hsaco.s") -replace '__hip_cuid_[0-9a-f]+','__hip_cuid_'
"prod ISA diff lines: $((Compare-Object $a $b).Count)"
Select-String -Path "$m\pair1\multihead-fast-padded-wave-packed.hsaco.s","$r\network-fixed-shapes\prod6-modules\multihead-fast-padded-wave-packed.hsaco.s" -Pattern '^\s+\.vgpr_count:|^\s+\.name:\s+mh_ffn_fused|\.group_segment_fixed_size:' | ForEach-Object { $_.Filename + ' ' + $_.Line.Trim() } > "$d\meta.txt"
'built'
