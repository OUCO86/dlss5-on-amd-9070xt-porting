param([int[]]$Heights=@(1080,900),[int[]]$Modes=@(3,4))
$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\c32-pair-encode";$assets='D:\DLSSNR-Lab\Magpie-DLSS5-AMD-0.23\DLSS5-AMD\native-game-tiled-assets'
$names=@{prefix='c32_fast_ffn_attention_fused_half_prefix_finish_main8';chain='c32_fast_ffn_attention_fused_half_chain';post='c32_post_merge_head_half'}
foreach($height in $Heights){foreach($mode in $Modes){foreach($target in 'prefix','chain','post'){
 & "$r\check-idle.ps1"
 $env:DLSS5_C32_PAIR_MODE="$mode";$env:DLSS5_C32_PROBE_TARGET=$names[$target]
 $folder="$d\fused-$height-$target-$mode";New-Item -ItemType Directory -Force $folder|Out-Null
 $w=if($height -eq 900){1600}else{1920};$h=if($height -eq 900){960}else{1152}
 $modules=if($mode -eq 4){"$d\modules-retain"}else{"$d\modules"}
 $p=Start-Process "$r\clock_observe_telemetry.exe" -ArgumentList '600' -PassThru -NoNewWindow -RedirectStandardOutput "$folder\telemetry.log" -RedirectStandardError "$folder\telemetry.err"
 Push-Location $folder
 try{& "$d\fused.exe" $assets $modules "$r\network-timeline\$height\flags.txt" "$r\network-timeline\$height\input.f32" "$r\network-timeline\$height\expected.f32" $w $h > run.log;if($LASTEXITCODE){throw "Fused test failed $height $target $mode"};Get-Content run.log}finally{Pop-Location;if(!$p.HasExited){Stop-Process -Id $p.Id -Force}}
}}}
Remove-Item Env:DLSS5_C32_PAIR_MODE,Env:DLSS5_C32_PROBE_TARGET -ErrorAction SilentlyContinue
