$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\network-fixed-shapes";$m="$d\modules"
if(Get-Process LOP-Win64-Shipping,SB-Win64-Shipping,OnimushaWotS,re9,Magpie -ErrorAction SilentlyContinue){throw 'Game running'}
New-Item -ItemType Directory -Force $m|Out-Null;Copy-Item "$r\mh-empty-c256-modules\*.hsaco" $m
foreach($arch in 'gfx1200','gfx1201'){
 $dest=if($arch -eq 'gfx1201'){$m}else{"$d\gfx1200"};New-Item -ItemType Directory -Force $dest|Out-Null
 foreach($pair in @(@('deep','deep_fast-packed'),@('mh','multihead-fast-padded-wave-packed'),@('attention','multihead_fused_attention'),@('reference','multihead-reference'))){
  & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$dest\$($pair[1]).hsaco" "$d\$($pair[0]).hip" comgr $arch
  if($LASTEXITCODE){throw 'Compile failed'}
 }
}
