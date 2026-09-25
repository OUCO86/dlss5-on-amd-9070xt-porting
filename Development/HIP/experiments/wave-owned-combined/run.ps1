param([int[]]$Heights=@(900,1080),[int]$Frames=200,[int]$Repeats=3,[string]$Candidates='3',[string]$Label='validate',[int]$DynamicFrames=16)
$ErrorActionPreference='Stop';$d=Split-Path -Parent $MyInvocation.MyCommand.Path;$r='D:\DLSSNR-Lab\hip-backend'
foreach($height in $Heights){
 & "$r\check-idle.ps1"
 $folder="$d\results-$height-$Label";New-Item -ItemType Directory -Force $folder | Out-Null
 $w=if($height -eq 900){1600}else{1920};$h=if($height -eq 900){960}else{1152}
 Push-Location $folder
 $env:W2_CANDIDATES=$Candidates;$env:W2_FRAG='1';$env:CW_DYNAMIC_FRAMES="$DynamicFrames"
 try{& "$d\network.exe" 'D:\DLSSNR-Lab\Magpie-DLSS5-AMD-0.23\DLSS5-AMD\native-game-tiled-assets' "$d\modules" "$r\network-timeline\$height\flags.txt" "$r\network-timeline\$height\input.f32" "$r\network-timeline\$height\expected.f32" $w $h $Frames $Repeats 2>&1 | Tee-Object run.log;if($LASTEXITCODE){throw 'combined probe failed'}}finally{Pop-Location}
}
