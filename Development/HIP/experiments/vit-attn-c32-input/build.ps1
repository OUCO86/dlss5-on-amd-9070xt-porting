# Compile the candidate modules (gfx1201) into modules-<Label> = production set + candidates.
param([string]$Label='cand')
$ErrorActionPreference='Stop'
$r='D:\DLSSNR-Lab\hip-backend';$d=Split-Path -Parent $MyInvocation.MyCommand.Path
$m="$d\modules-$Label";New-Item -ItemType Directory -Force $m | Out-Null
Copy-Item "$r\vit-proj-n64-production\modules-gfx1201\*.hsaco" $m
$manifest=@{label=$Label}
foreach($pair in @(@('mh.hip','vac-mh.hsaco'),@('deep.hip','vac-deep.hsaco'),@('c32.hip','vac-c32.hsaco'))){
 if(!(Test-Path "$d\$($pair[0])")){continue}
 $source="$m\$($pair[0])";Copy-Item "$d\$($pair[0])" $source
 & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$m\$($pair[1])" $source comgr gfx1201
 if($LASTEXITCODE){throw "Compile failed $($pair[0])"}
 $manifest[$pair[1]]=(Get-FileHash "$m\$($pair[1])").Hash;$manifest[$pair[0]]=(Get-FileHash $source).Hash
}
[IO.File]::WriteAllText("$m\build-manifest.json",($manifest|ConvertTo-Json),(New-Object Text.UTF8Encoding($false)))
$manifest|ConvertTo-Json
