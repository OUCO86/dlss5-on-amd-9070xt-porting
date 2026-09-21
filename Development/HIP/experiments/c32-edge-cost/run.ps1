param([int[]]$Heights=@(900,1080),[string[]]$Targets=@('prefix','chain','post'))
$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\c32-edge-cost";$a='D:\DLSSNR-Lab\Magpie-DLSS5-AMD-0.23\DLSS5-AMD'
Remove-Item Env:DLSS5_C32_PROBE_PHASE -ErrorAction SilentlyContinue
$names=@{prefix='c32_fast_ffn_attention_fused_half_prefix_finish_main8';chain='c32_fast_ffn_attention_fused_half_chain';post='c32_post_merge_head_half'}
foreach($height in $Heights){foreach($target in $Targets){
 if(Get-Process LOP-Win64-Shipping,SB-Win64-Shipping,OnimushaWotS,re9,Magpie -ErrorAction SilentlyContinue){throw 'Game running'}
 if(!$names.ContainsKey($target)){throw 'Unknown target'}
 $env:DLSS5_C32_PROBE_TARGET=$names[$target];$folder="$d\$height-$target";New-Item -ItemType Directory -Force $folder|Out-Null
 $w=if($height -eq 900){1600}else{1920};$h=if($height -eq 900){960}else{1152}
 Push-Location $folder
 try{& "$d\pure.exe" "$a\native-game-tiled-assets" "$d\modules" "$r\network-timeline\$height\flags.txt" "$r\network-timeline\$height\input.f32" "$r\network-timeline\$height\expected.f32" $w $h > run.log;if($LASTEXITCODE){throw "Phase probe failed $height $target"};Get-Content run.log}finally{Pop-Location}
}}
Remove-Item Env:DLSS5_C32_PROBE_TARGET,Env:DLSS5_C32_PROBE_PHASE -ErrorAction SilentlyContinue
