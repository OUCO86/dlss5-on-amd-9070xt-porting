# prod7 candidate = prod6 + HIP_FFN_LINE_STORES=1 in mh_fast (bit-exact, mhfast-line-stores-20260924). Only the mh_fast module changes.
$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\fence-prod7"
& "$r\check-idle.ps1"
$m="$r\network-fixed-shapes\prod7-modules";New-Item -ItemType Directory -Force $m|Out-Null
Copy-Item "$r\network-fixed-shapes\prod6-modules\*.hsaco" $m
$g="$r\network-fixed-shapes\prod7-gfx1200";New-Item -ItemType Directory -Force $g|Out-Null
Copy-Item "$r\network-fixed-shapes\prod6-gfx1200\*.hsaco" $g
foreach($arch in 'gfx1200','gfx1201'){
 $dest=if($arch -eq 'gfx1201'){$m}else{$g}
 & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$dest\multihead-fast-padded-wave-packed.hsaco" "$d\mhfast.generated.hip" comgr $arch | Out-Null
 if($LASTEXITCODE){throw "Compile failed $arch"}
 "$arch multihead-fast-padded-wave-packed "+(Get-FileHash "$dest\multihead-fast-padded-wave-packed.hsaco").Hash
}
