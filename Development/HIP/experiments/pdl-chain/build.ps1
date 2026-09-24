param([string]$Variant='')
$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\pdl-chain";$m=if($Variant){"$d\modules-$Variant"}else{"$d\modules"};$sfx=if($Variant){".$Variant"}else{''}
& "$r\check-idle.ps1"
New-Item -ItemType Directory -Force $m|Out-Null
Copy-Item "$r\network-fixed-shapes\prod7-modules\*.hsaco" $m
& 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$m\multihead-fast-padded-wave-packed.hsaco" "$d\mhfast$sfx.generated.hip" comgr gfx1201 | Out-Null
if($LASTEXITCODE){throw 'mh_fast compile failed'}
& 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$m\multihead_fused_attention.hsaco" "$d\mhfused$sfx.generated.hip" comgr gfx1201 | Out-Null
if($LASTEXITCODE){throw 'mh_fused compile failed'}
Select-String -Path "$m\multihead-fast-padded-wave-packed.hsaco.s","$m\multihead_fused_attention.hsaco.s" -Pattern '^\s+\.name:\s+\S+_pdl$' | ForEach-Object { $_.Line.Trim() }
'built'
