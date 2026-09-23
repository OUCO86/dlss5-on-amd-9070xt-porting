$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\mh-hoist-residual";$m="$d\modules"
& "$r\check-idle.ps1"
New-Item -ItemType Directory -Force $m|Out-Null
Copy-Item "$r\network-fixed-shapes\prod5-modules\*.hsaco" $m
Copy-Item "$r\mhfast-tail-ablate\network.exe" "$d\network.exe"
foreach($pm in 1,2,3){
 $dest="$m\pair$pm";New-Item -ItemType Directory -Force $dest|Out-Null
 foreach($name in 'c32_fused_ffn_attention-packed','deep_fast-packed','multihead-fast-padded-wave-packed'){Copy-Item "$m\$name.hsaco" "$dest\$name.hsaco"}
 & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$dest\multihead_fused_attention.hsaco" "$d\pair$pm\multihead_fused_attention.generated.hip" comgr gfx1201
 if($LASTEXITCODE){throw "Compile failed $pm"}
}
