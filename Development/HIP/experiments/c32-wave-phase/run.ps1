param([int[]]$Heights=@(900,1080),[int]$Frames=80,[string]$Phases='0,1,2,3,4,5,6,7,8,9,10',[string]$Label='')
$ErrorActionPreference='Stop'
$r='D:\DLSSNR-Lab\hip-backend';$d=Split-Path -Parent $MyInvocation.MyCommand.Path
$assets='D:\DLSSNR-Lab\Magpie-DLSS5-AMD-0.23\DLSS5-AMD\native-game-tiled-assets'
foreach($height in $Heights){
 if($height -notin @(900,1080)){throw 'height'}
 & "$r\check-idle.ps1"
 $folder="$d\results-$height$Label";New-Item -ItemType Directory -Force $folder | Out-Null
 $w=if($height -eq 900){1600}else{1920};$h=if($height -eq 900){960}else{1152}
 Push-Location $folder
 $env:C32_TRACE_PHASES=$Phases
 try{& "$d\network.exe" $assets "$d\modules" "$r\network-timeline\$height\flags.txt" "$r\network-timeline\$height\input.f32" "$r\network-timeline\$height\expected.f32" $w $h $Frames 2>&1 | Tee-Object run.log;if($LASTEXITCODE){throw "Trace failed $height"}}finally{Pop-Location}
}
