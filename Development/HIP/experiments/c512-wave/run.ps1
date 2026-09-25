# ABBA production (mode 0) vs +C512 one-head-one-wave (mode 1); every slot's first/last RGB bit-checked, then dynamic history frames.
param([int[]]$Heights=@(900,1080),[int]$Frames=200,[int]$Repeats=3,[string]$Label='base',[int]$Pdl=1,[string]$Candidates='1')
$ErrorActionPreference='Stop'
$r='D:\DLSSNR-Lab\hip-backend';$d=Split-Path -Parent $MyInvocation.MyCommand.Path;$a='D:\DLSSNR-Lab\Magpie-DLSS5-AMD-0.23\DLSS5-AMD';$cap="$r\network-timeline"
function Idle{$p=Get-Process LOP-Win64-Shipping,SB-Win64-Shipping,Cyberpunk2077,OnimushaWotS,re9,Magpie -ErrorAction SilentlyContinue;if($p){throw "Game running: $($p.ProcessName -join ',')"}}
foreach($height in $Heights){
 Idle;$f="$d\results-$height-$Label";New-Item -ItemType Directory -Force $f|Out-Null
 $flags=@(Get-Content "$a\native-game-flags.txt")+@('DLSS5_HIP_MH_FEATURE_BYTE=1','DLSS5_HIP_MH_PROJ_DIAG_FB=1','DLSS5_HIP_MH_BYTE_STREAM=1','DLSS5_HIP_DECODER_BYTE=1','DLSS5_HIP_VIT_BYTE_STREAM=0','DLSS5_HIP_MH_FFN_FRAG256=1','DLSS5_HIP_GRAPH=0','DLSS5_VIT_ADAPTIVE=0',"DLSS5_NETWORK_HEIGHT=$height","DLSS5_HIP_PDL=$Pdl",'DLSS5_HIP_WAVE_OWNED=1')
 [IO.File]::WriteAllLines("$f\flags.txt",$flags)
 $w=if($height -eq 900){1600}else{1920};$h=if($height -eq 900){960}else{1152}
 Push-Location $f;$env:C5_CANDIDATES=$Candidates
 try{& "$d\network.exe" "$a\native-game-tiled-assets" "$d\modules-$Label" "$f\flags.txt" "$cap\$height\input.f32" "$cap\$height\expected.f32" $w $h $Frames $Repeats > run.log 2>&1;$code=$LASTEXITCODE;Get-Content run.log|Select-String 'CONFIG|C512_CALLS|SLOT|PASS|FAIL'|Select-Object -Last 20;if($code){throw "c512 wave failed $height $Label"}}finally{Pop-Location}
}
