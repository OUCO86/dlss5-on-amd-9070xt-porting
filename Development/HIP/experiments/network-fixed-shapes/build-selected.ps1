$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\network-fixed-shapes";$m="$d\selected-modules"
if(Get-Process LOP-Win64-Shipping,SB-Win64-Shipping,OnimushaWotS,re9,Magpie -ErrorAction SilentlyContinue){throw 'Game running'}
New-Item -ItemType Directory -Force $m|Out-Null;Copy-Item "$r\mh-empty-c256-modules\*.hsaco" $m
foreach($arch in 'gfx1200','gfx1201'){
 $dest=if($arch -eq 'gfx1201'){$m}else{"$d\selected-gfx1200"};New-Item -ItemType Directory -Force $dest|Out-Null
 foreach($pair in @(@('packed','deep_fast-packed'),@('unpacked','deep_fast'))){
  & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$dest\$($pair[1]).hsaco" "$d\selected-$($pair[0]).hip" comgr $arch
  if($LASTEXITCODE){throw 'Compile failed'}
 }
}
