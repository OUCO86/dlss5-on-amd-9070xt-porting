$ErrorActionPreference='Stop'
$d=Split-Path -Parent $MyInvocation.MyCommand.Path
& "$d\build-candidate.ps1" 2>&1 | Tee-Object "$d\build-candidate.log"
& "$d\regression.ps1" -CorrectnessOnly 2>&1 | Tee-Object "$d\regression.log"
& "$d\regression.ps1" -ExtraControls 2>&1 | Tee-Object "$d\extra-controls.log"
