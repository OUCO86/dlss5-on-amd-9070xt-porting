param([int[]]$Heights=@(900,1080),[int]$Frames=160,[int]$Repeats=3,[string]$Candidates='1,2,3,4',[ValidateSet('row','frag')][string]$Layout='row',[switch]$DeferQ,[switch]$DirectFeature,[switch]$Launder,[switch]$Schedule,[switch]$RollQuery,[ValidateSet(1,2,4,8)][int]$HiddenTiles=1,[string]$Label='')
$ErrorActionPreference='Stop';$d=Split-Path -Parent $MyInvocation.MyCommand.Path
& "$d\build.ps1" -Layout $Layout -DeferQ:$DeferQ -DirectFeature:$DirectFeature -Launder:$Launder -Schedule:$Schedule -RollQuery:$RollQuery -HiddenTiles $HiddenTiles
& "$d\run.ps1" -Heights $Heights -Frames $Frames -Repeats $Repeats -Candidates $Candidates -Layout $Layout -DeferQ:$DeferQ -DirectFeature:$DirectFeature -Launder:$Launder -Schedule:$Schedule -RollQuery:$RollQuery -HiddenTiles $HiddenTiles -Label $Label
