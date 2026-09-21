$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\network-timeline";$a='D:\DLSSNR-Lab\Magpie-DLSS5-AMD-0.23\DLSS5-AMD';$m="$r\mh-empty-c256-modules"
function Idle {if(Get-Process LOP-Win64-Shipping,SB-Win64-Shipping,OnimushaWotS,re9,Magpie -ErrorAction SilentlyContinue){throw 'Game running'}}
$expected=@{900='75AABA5EF94368353F3F17C034B53918151AA2EBC98FF870B2A057D08AE910AB';1080='1DE20C219105CC281CBA1364A0A21D0DDC4510A95458EC0CA3B8C893EA54F23A'}
foreach($height in 900,1080){
 Idle;$folder="$d\$height";New-Item -ItemType Directory -Force $folder|Out-Null
 $flags=@(Get-Content "$r\mh-empty-c256-results\base-$height-0\flags.txt")+@('DLSS5_HIP_GRAPH=0','DLSS5_VIT_ADAPTIVE=0','DLSS5_HIP_FAST=1')
 [IO.File]::WriteAllLines("$folder\flags.txt",$flags)
 Push-Location $folder
 try{
  & "$d\dump.exe" "$a\native-game-tiled-assets" "$folder\flags.txt" "$r\live-menu-before.f16" "$folder\rgb" 12 0 $m 0 1 0 0 > dump.log
  if($LASTEXITCODE){throw 'Dump failed'}
  if((Get-FileHash "$folder\rgb.f16").Hash -ne $expected[$height]){throw 'Capture output mismatch'}
  Idle;$w=if($height -eq 900){1600}else{1920};$h=if($height -eq 900){960}else{1152}
  & "$d\pure.exe" "$a\native-game-tiled-assets" $m "$folder\flags.txt" "$folder\input.f32" "$folder\expected.f32" $w $h > run.log
  if($LASTEXITCODE){throw 'Timeline failed'}
  Get-Content run.log
 }finally{Pop-Location}
}
