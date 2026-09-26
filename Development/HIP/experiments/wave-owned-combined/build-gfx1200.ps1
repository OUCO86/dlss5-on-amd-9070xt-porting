$ErrorActionPreference='Stop';$d=Split-Path -Parent $MyInvocation.MyCommand.Path;$r='D:\DLSSNR-Lab\hip-backend'
& "$r\check-idle.ps1"
$m="$d\modules-gfx1200";New-Item -ItemType Directory -Force $m | Out-Null
Copy-Item "$r\network-fixed-shapes\prod8-gfx1200\*.hsaco" $m
foreach($pair in @(@('c64-wave2',"$r\c64-wave2\modules-frag-launder-sched-roll-ht2\build.hip"),@('c32-wave1',"$r\c32-wave1\modules-rollh-rw\build.hip"))){
 & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$m\$($pair[0]).hsaco" $pair[1] comgr gfx1200
 if($LASTEXITCODE){throw "compile failed $($pair[0])"}
}
$manifest=Get-ChildItem "$m\*.hsaco" | ForEach-Object {@{name=$_.Name;sha256=(Get-FileHash $_.FullName).Hash}}
[IO.File]::WriteAllText("$d\gfx1200-manifest.json",($manifest|ConvertTo-Json),(New-Object Text.UTF8Encoding($false)))
