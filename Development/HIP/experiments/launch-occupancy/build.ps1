$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\launch-occupancy"
& "$r\check-idle.ps1"
$sets=@{c32='c32_fused_ffn_attention-packed';mhfast='multihead-fast-padded-wave-packed';mh='multihead_fused_attention'}
foreach($tag in $sets.Keys){
 $m="$d\$tag\modules";New-Item -ItemType Directory -Force $m|Out-Null
 Copy-Item "$r\network-fixed-shapes\prod5-modules\*.hsaco" $m
 & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$m\$($sets[$tag]).hsaco" "$d\$tag\kernel.hip" comgr gfx1201
 if($LASTEXITCODE){throw "Compile failed $tag"}
 Write-Host "built $tag"
}
