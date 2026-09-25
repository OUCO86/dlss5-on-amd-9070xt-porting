$ErrorActionPreference='Stop';$d=Split-Path -Parent $MyInvocation.MyCommand.Path;$r='D:\DLSSNR-Lab\hip-backend'
New-Item -ItemType Directory -Force "$d\modules" | Out-Null
Copy-Item "$r\network-fixed-shapes\prod8-modules\*.hsaco" "$d\modules"
Copy-Item "$r\c64-wave2\modules-frag-launder-sched-roll-ht2\c64-wave2.hsaco" "$d\modules"
Copy-Item "$r\c32-wave1\modules-rollh-rw\c32-wave1.hsaco" "$d\modules"
$manifest=Get-ChildItem "$d\modules\*.hsaco" | ForEach-Object {@{name=$_.Name;sha256=(Get-FileHash $_.FullName).Hash}}
[IO.File]::WriteAllText("$d\modules-manifest.json",($manifest|ConvertTo-Json),(New-Object Text.UTF8Encoding($false)))
