# prod8 candidate = prod7 + _pdl kernel twins in mh_fast and mh_fused (extra exports; original kernels' code unchanged) + host
# any-order chain launches (DLSS5_HIP_PDL=1). Bit-exact (results/pdl-chain-20260925). Two modules change, both architectures.
$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\prod8"
& "$r\check-idle.ps1"
$m="$r\network-fixed-shapes\prod8-modules";New-Item -ItemType Directory -Force $m|Out-Null
Copy-Item "$r\network-fixed-shapes\prod7-modules\*.hsaco" $m
$g="$r\network-fixed-shapes\prod8-gfx1200";New-Item -ItemType Directory -Force $g|Out-Null
Copy-Item "$r\network-fixed-shapes\prod7-gfx1200\*.hsaco" $g
foreach($arch in 'gfx1200','gfx1201'){
 $dest=if($arch -eq 'gfx1201'){$m}else{$g}
 foreach($pair in @(@('multihead-fast-padded-wave-packed','mhfast'),@('multihead_fused_attention','mhfused'))){
  & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$dest\$($pair[0]).hsaco" "$d\$($pair[1]).generated.hip" comgr $arch | Out-Null
  if($LASTEXITCODE){throw "Compile failed $arch $($pair[0])"}
  "$arch $($pair[0]) "+(Get-FileHash "$dest\$($pair[0]).hsaco").Hash
 }
}
'built'
