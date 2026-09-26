param([int[]]$Heights=@(900,1080),[int]$Frames=160,[int]$Repeats=3,[string]$Candidates='1,2,3',[string]$Label='')
$ErrorActionPreference='Stop'
$d=Split-Path -Parent $MyInvocation.MyCommand.Path
& "$d\build.ps1"
& "$d\run.ps1" -Heights $Heights -Frames $Frames -Repeats $Repeats -Candidates $Candidates -Label $Label
