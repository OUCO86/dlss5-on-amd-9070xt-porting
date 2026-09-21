param([int[]]$Heights=@(900,1080),[string[]]$Targets=@('expand','contract'))
$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\vit-ffn-ladder";$a='D:\DLSSNR-Lab\Magpie-DLSS5-AMD-0.23\DLSS5-AMD'
Remove-Item Env:DLSS5_C32_PROBE_PHASE -ErrorAction SilentlyContinue
$names=@{expand='vit_expand_blocked_fp8_frag_bytein';contract='vit_contract_blocked_fp8_frag'}
foreach($height in $Heights){foreach($target in $Targets){
 if(Get-Process LOP-Win64-Shipping,SB-Win64-Shipping,OnimushaWotS,re9,Magpie -ErrorAction SilentlyContinue){throw 'Game running'}
 if(!$names.ContainsKey($target)){throw 'Unknown target'}
 $env:DLSS5_C32_PROBE_TARGET=$names[$target];$folder="$d\$height-$target";New-Item -ItemType Directory -Force $folder|Out-Null
 $w=if($height -eq 900){1600}else{1920};$h=if($height -eq 900){960}else{1152}
 Push-Location $folder
 try{& "$d\pure.exe" "$a\native-game-tiled-assets" "$d\modules" "$r\network-timeline\$height\flags.txt" "$r\network-timeline\$height\input.f32" "$r\network-timeline\$height\expected.f32" $w $h > run.log;if($LASTEXITCODE){throw "Phase probe failed $height $target"};Get-Content run.log}finally{Pop-Location}
}}
Remove-Item Env:DLSS5_C32_PROBE_TARGET,Env:DLSS5_C32_PROBE_PHASE -ErrorAction SilentlyContinue
