$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\fence-prod2"
& "$r\check-idle.ps1"
$m="$r\network-fixed-shapes\prod2-modules";New-Item -ItemType Directory -Force $m|Out-Null
Copy-Item "$r\network-fixed-shapes\fence-modules\*.hsaco" $m
$g="$r\network-fixed-shapes\prod2-gfx1200";New-Item -ItemType Directory -Force $g|Out-Null
Copy-Item "$r\network-fixed-shapes\fence-gfx1200\*.hsaco" $g
foreach($arch in 'gfx1200','gfx1201'){
 $dest=if($arch -eq 'gfx1201'){$m}else{$g}
 & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$dest\c32_fused_ffn_attention-packed.hsaco" "$d\c32_fused_ffn_attention-packed.generated.hip" comgr $arch | Out-Null
 if($LASTEXITCODE){throw "Compile failed $arch"}
 "$arch "+(Get-FileHash "$dest\c32_fused_ffn_attention-packed.hsaco").Hash
}
