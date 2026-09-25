param([int[]]$Heights=@(900,1080),[int]$Frames=160,[int]$Repeats=3,[string]$Candidates='1,2,3,4',[ValidateSet('row','frag')][string]$Layout='row',[switch]$DeferQ,[switch]$Launder,[switch]$Schedule,[switch]$RollQuery,[ValidateSet(1,2,4,8)][int]$HiddenTiles=1,[string]$Label='')
$ErrorActionPreference='Stop'
$r='D:\DLSSNR-Lab\hip-backend';$d=Split-Path -Parent $MyInvocation.MyCommand.Path
$assets='D:\DLSSNR-Lab\Magpie-DLSS5-AMD-0.23\DLSS5-AMD\native-game-tiled-assets'
$suffix=if($DeferQ){'-defer'}else{''}
if($Launder){$suffix+='-launder'}
if($Schedule){$suffix+='-sched'}
if($RollQuery){$suffix+='-roll'}
if($HiddenTiles -ne 1){$suffix+="-ht$HiddenTiles"}
foreach($height in $Heights){
 & "$r\check-idle.ps1"
 $folder="$d\results-$height-$Layout$suffix$Label";New-Item -ItemType Directory -Force $folder | Out-Null
 $w=if($height -eq 900){1600}else{1920};$h=if($height -eq 900){960}else{1152}
 Push-Location $folder
 $env:W2_CANDIDATES=$Candidates;$env:W2_FRAG=if($Layout -eq 'frag'){'1'}else{'0'}
 try{& "$d\network.exe" $assets "$d\modules-$Layout$suffix" "$r\network-timeline\$height\flags.txt" "$r\network-timeline\$height\input.f32" "$r\network-timeline\$height\expected.f32" $w $h $Frames $Repeats 2>&1 | Tee-Object run.log;if($LASTEXITCODE){throw "Wave2 failed $height $Layout"}}finally{Pop-Location}
}
