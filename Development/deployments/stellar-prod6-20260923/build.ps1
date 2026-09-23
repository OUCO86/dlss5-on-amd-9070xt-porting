$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\fence-prod6"
& "$r\check-idle.ps1"
$m="$r\network-fixed-shapes\prod6-modules";New-Item -ItemType Directory -Force $m|Out-Null
Copy-Item "$r\network-fixed-shapes\prod5-modules\*.hsaco" $m
$g="$r\network-fixed-shapes\prod6-gfx1200";New-Item -ItemType Directory -Force $g|Out-Null
Copy-Item "$r\network-fixed-shapes\prod5-gfx1200\*.hsaco" $g
foreach($arch in 'gfx1200','gfx1201'){
 $dest=if($arch -eq 'gfx1201'){$m}else{$g}
 foreach($pair in @(@('c32_fused_ffn_attention-packed','c32.generated.hip'),@('multihead-fast-padded-wave-packed','mhfast.generated.hip'))){
  & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$dest\$($pair[0]).hsaco" "$d\$($pair[1])" comgr $arch | Out-Null
  if($LASTEXITCODE){throw "Compile failed $arch $($pair[0])"}
  "$arch $($pair[0]) "+(Get-FileHash "$dest\$($pair[0]).hsaco").Hash
 }
}
