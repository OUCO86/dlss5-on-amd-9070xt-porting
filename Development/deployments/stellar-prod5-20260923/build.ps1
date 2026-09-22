$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\fence-prod5"
& "$r\check-idle.ps1"
$m="$r\network-fixed-shapes\prod5-modules";New-Item -ItemType Directory -Force $m|Out-Null
Copy-Item "$r\network-fixed-shapes\prod4-modules\*.hsaco" $m
$g="$r\network-fixed-shapes\prod5-gfx1200";New-Item -ItemType Directory -Force $g|Out-Null
Copy-Item "$r\network-fixed-shapes\prod4-gfx1200\*.hsaco" $g
foreach($arch in 'gfx1200','gfx1201'){
 $dest=if($arch -eq 'gfx1201'){$m}else{$g}
 & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$dest\multihead_fused_attention.hsaco" "$d\multihead_fused_attention.generated.hip" comgr $arch | Out-Null
 if($LASTEXITCODE){throw "Compile failed $arch"}
 "$arch "+(Get-FileHash "$dest\multihead_fused_attention.hsaco").Hash
}
