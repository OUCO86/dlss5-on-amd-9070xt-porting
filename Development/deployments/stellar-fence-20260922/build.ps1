$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\fence-prod"
& "$r\check-idle.ps1"
$m="$r\network-fixed-shapes\fence-modules";New-Item -ItemType Directory -Force $m|Out-Null
Copy-Item "$r\network-fixed-shapes\selected-modules\*.hsaco" $m
$g="$r\network-fixed-shapes\fence-gfx1200";New-Item -ItemType Directory -Force $g|Out-Null
foreach($arch in 'gfx1200','gfx1201'){
 $dest=if($arch -eq 'gfx1201'){$m}else{$g}
 foreach($name in 'c32_fused_ffn_attention-packed','multihead_fused_attention','deep_fast','deep_fast-packed','multihead-fast-padded-wave-packed'){
  & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$dest\$name.hsaco" "$d\$name.generated.hip" comgr $arch | Out-Null
  if($LASTEXITCODE){throw "Compile failed $arch $name"}
  "$arch $name "+(Get-FileHash "$dest\$name.hsaco").Hash
 }
}
