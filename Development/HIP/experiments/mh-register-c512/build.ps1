$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\mh-register-c512";$m="$d\modules"
& "$r\check-idle.ps1"
New-Item -ItemType Directory -Force $m|Out-Null
Copy-Item "$r\network-fixed-shapes\prod5-modules\*.hsaco" $m
Copy-Item "$r\fence-scope-all\network.exe" $d
foreach($pm in 1,2,3){
 $dest="$m\pair$pm";New-Item -ItemType Directory -Force $dest|Out-Null
 foreach($n in 'c32_fused_ffn_attention-packed','deep_fast-packed','multihead-fast-padded-wave-packed'){Copy-Item "$r\network-fixed-shapes\prod5-modules\$n.hsaco" $dest}
 if($pm -eq 1){& 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$dest\multihead_fused_attention.hsaco" "$d\multihead_fused_attention.generated.hip" comgr gfx1201; if($LASTEXITCODE){throw 'Compile failed'}}
 else{Copy-Item "$m\pair1\multihead_fused_attention.hsaco" $dest;Copy-Item "$m\pair1\multihead_fused_attention.hsaco.s" $dest}
}
'built'
