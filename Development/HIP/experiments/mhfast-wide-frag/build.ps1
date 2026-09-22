$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\mhfast-wide-frag";$m="$d\modules"
& "$r\check-idle.ps1"
New-Item -ItemType Directory -Force $m|Out-Null
Copy-Item "$r\network-fixed-shapes\prod5-modules\*.hsaco" $m
foreach($pm in 1,2,3){
 $dest="$m\pair$pm";New-Item -ItemType Directory -Force $dest|Out-Null
 foreach($n in 'c32_fused_ffn_attention-packed','multihead_fused_attention','deep_fast-packed'){Copy-Item "$r\network-fixed-shapes\prod5-modules\$n.hsaco" $dest}
 if($pm -eq 1){& 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$dest\multihead-fast-padded-wave-packed.hsaco" "$d\multihead-fast-padded-wave-packed.generated.hip" comgr gfx1201; if($LASTEXITCODE){throw 'Compile failed'}}
 else{Copy-Item "$m\pair1\multihead-fast-padded-wave-packed.hsaco" $dest}
}
'built'
