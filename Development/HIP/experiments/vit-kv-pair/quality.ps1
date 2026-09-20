$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$lab='D:\DLSSNR-Lab';$b="$lab\Magpie-DLSS5-AMD-0.23\DLSS5-AMD";$work="$r\profile1080"
function Idle {if(Get-Process re9,SB-Win64-Shipping,LOP-Win64-Shipping,Magpie -ErrorAction SilentlyContinue){throw 'Game/Magpie running'}}
$flags=@(Get-Content "$b\native-game-flags.txt")+@('DLSS5_HIP_MH_FEATURE_BYTE=1','DLSS5_HIP_MH_PROJ_DIAG_FB=1','DLSS5_HIP_MH_BYTE_STREAM=1','DLSS5_HIP_DECODER_BYTE=1','DLSS5_HIP_VIT_BYTE_STREAM=0','DLSS5_HIP_MH_FFN_FRAG256=1','DLSS5_HIP_GRAPH=0','DLSS5_SHOW_FPS=0','DLSS5_PRE_UPSCALE=0')
foreach($height in 900,1080){foreach($pattern in 0,1,2){foreach($variant in 'base','pair'){
 Idle;$m=if($variant -eq 'base'){"$lab\c256-frag-production-modules\gfx1201"}else{"$r\vit-kv-pair-modules"};$prefix="$work\vitpair-quality-$height-$pattern-$variant";$f="$work\vitpair-quality-flags.txt";[IO.File]::WriteAllLines($f,($flags+@("DLSS5_NETWORK_HEIGHT=$height")))
 & "$r\benchmark_c256frag_production.exe" "$b\native-game-tiled-assets" $f "$r\live-menu-before.f16" $prefix 12 0 $m 0 0 0 $pattern > "$prefix.log"
 if($LASTEXITCODE){throw 'Quality replay failed'}
 $rows=@(Import-Csv "$prefix.csv");if($rows.Count -ne 12 -or @($rows|Where-Object{[int]$_.invalid -ne 0}).Count){throw 'Nonfinite/missing frames'}
 "$height pattern=$pattern $variant finite=12/12"
 Idle
}}}
