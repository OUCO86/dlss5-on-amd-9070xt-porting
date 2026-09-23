$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\mhfast-tail-ablate";$m="$d\modules"
& "$r\check-idle.ps1"
New-Item -ItemType Directory -Force $m|Out-Null
Copy-Item "$r\network-fixed-shapes\prod5-modules\*.hsaco" $m

foreach($pm in 1,2,3){
 $dest="$m\pair$pm";New-Item -ItemType Directory -Force $dest|Out-Null
 foreach($name in 'c32_fused_ffn_attention-packed','multihead_fused_attention','deep_fast-packed'){Copy-Item "$m\$name.hsaco" "$dest\$name.hsaco"}
 & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$dest\multihead-fast-padded-wave-packed.hsaco" "$d\pair$pm\multihead-fast-padded-wave-packed.generated.hip" comgr gfx1201
 if($LASTEXITCODE){throw "Compile failed $pm"}
}
