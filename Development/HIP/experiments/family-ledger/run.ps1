# Family ledger on the wave-owned production state: PDL 1/0 x 900/1080, sparse-prefix localABBA, raw FP32 bit checks vs captured expected.
$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\family-ledger";$a='D:\DLSSNR-Lab\Magpie-DLSS5-AMD-0.23\DLSS5-AMD';$m="$r\wave-owned-production\modules-gfx1201";$cap="$r\network-timeline"
function Idle{$p=Get-Process LOP-Win64-Shipping,SB-Win64-Shipping,Cyberpunk2077,OnimushaWotS,re9,Magpie -ErrorAction SilentlyContinue;if($p){throw "Game running: $($p.ProcessName -join ',')"}}
foreach($pdl in 1,0){foreach($height in 900,1080){
 Idle;$f="$d\$height-pdl$pdl";New-Item -ItemType Directory -Force $f|Out-Null
 $flags=@(Get-Content "$a\native-game-flags.txt")+@('DLSS5_HIP_MH_FEATURE_BYTE=1','DLSS5_HIP_MH_PROJ_DIAG_FB=1','DLSS5_HIP_MH_BYTE_STREAM=1','DLSS5_HIP_DECODER_BYTE=1','DLSS5_HIP_VIT_BYTE_STREAM=0','DLSS5_HIP_MH_FFN_FRAG256=1','DLSS5_HIP_GRAPH=0','DLSS5_VIT_ADAPTIVE=0',"DLSS5_NETWORK_HEIGHT=$height","DLSS5_HIP_PDL=$pdl",'DLSS5_HIP_WAVE_OWNED=1')
 [IO.File]::WriteAllLines("$f\flags.txt",$flags)
 $w=if($height -eq 900){1600}else{1920};$h=if($height -eq 900){960}else{1152}
 Push-Location $f
 try{& "$d\ledger.exe" "$a\native-game-tiled-assets" $m "$f\flags.txt" "$cap\$height\input.f32" "$cap\$height\expected.f32" $w $h > run.log 2>&1;$code=$LASTEXITCODE;Get-Content run.log|Select-String 'CONFIG|TOPOLOGY|PASS|FAIL|VERIFY label=(warm|final)';if($code){throw "ledger failed $height pdl$pdl"}}finally{Pop-Location}
}}
