param([int[]]$Heights=@(900,1080),[int]$Frames=80,[int]$Repeats=1,[string]$Label='probe',[switch]$Launder,[switch]$RollHidden)
$ErrorActionPreference='Stop';$d=Split-Path -Parent $MyInvocation.MyCommand.Path;$r='D:\DLSSNR-Lab\hip-backend'
$suffix=if($Launder){'-launder'}else{''}
if($RollHidden){$suffix+='-rollh'}
foreach($height in $Heights){
 & "$r\check-idle.ps1"
 $folder="$d\results-$height$suffix-$Label";New-Item -ItemType Directory -Force $folder | Out-Null
 $w=if($height -eq 900){1600}else{1920};$h=if($height -eq 900){960}else{1152}
 Push-Location $folder
 $env:W2_CANDIDATES='1'
 try{& "$d\network.exe" 'D:\DLSSNR-Lab\Magpie-DLSS5-AMD-0.23\DLSS5-AMD\native-game-tiled-assets' "$d\modules$suffix" "$r\network-timeline\$height\flags.txt" "$r\network-timeline\$height\input.f32" "$r\network-timeline\$height\expected.f32" $w $h $Frames $Repeats 2>&1 | Tee-Object run.log;if($LASTEXITCODE){throw 'c32 probe failed'}}finally{Pop-Location}
}
