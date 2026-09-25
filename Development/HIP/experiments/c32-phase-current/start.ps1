param([int[]]$Heights=@(900,1080),[int]$Frames=80,[string]$Phases='0,1,2,3,4,5,6,7,8,9,10',[string]$Label='')
$ErrorActionPreference='Stop';$d=Split-Path -Parent $MyInvocation.MyCommand.Path
& "$d\build.ps1"
& "$d\run.ps1" -Heights $Heights -Frames $Frames -Phases $Phases -Label $Label
