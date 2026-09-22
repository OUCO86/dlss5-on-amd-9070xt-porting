$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\fence-scope-all";$m="$d\modules"
& "$r\check-idle.ps1"
New-Item -ItemType Directory -Force $m|Out-Null
Copy-Item "$r\network-fixed-shapes\selected-modules\*.hsaco" $m
foreach($pm in 1,2){
 foreach($arch in 'gfx1200','gfx1201'){
  $dest=if($arch -eq 'gfx1201'){"$m\pair$pm"}else{"$d\gfx1200-pair$pm"}
  New-Item -ItemType Directory -Force $dest|Out-Null
  foreach($name in 'c32_fused_ffn_attention-packed','multihead_fused_attention','deep_fast-packed','multihead-fast-padded-wave-packed'){
   & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$dest\$name.hsaco" "$d\pair$pm\$name.generated.hip" comgr $arch
   if($LASTEXITCODE){throw "Compile failed $pm $arch $name"}
  }
 }
}
