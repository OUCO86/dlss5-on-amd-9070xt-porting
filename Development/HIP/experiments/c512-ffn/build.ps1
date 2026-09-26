# Compile c512-ffn.hsaco (gfx1201) next to a copy of the wave-owned production module set.
param([string]$Label='cand')
$ErrorActionPreference='Stop'
$r='D:\DLSSNR-Lab\hip-backend';$d=Split-Path -Parent $MyInvocation.MyCommand.Path
$m="$d\modules-$Label";New-Item -ItemType Directory -Force $m | Out-Null
Copy-Item "$r\wave-owned-production\modules-gfx1201\*.hsaco" $m
$source="$m\build.hip";Copy-Item "$d\kernel.hip" $source
& 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$m\c512-ffn.hsaco" $source comgr gfx1201
if($LASTEXITCODE){throw 'Compile failed'}
$dsource="$m\deep.hip";Copy-Item "$d\deep.hip" $dsource
& 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$m\c512-deep.hsaco" $dsource comgr gfx1201
if($LASTEXITCODE){throw 'Deep compile failed'}
$manifest=@{label=$Label;source_sha256=(Get-FileHash $source).Hash;module_sha256=(Get-FileHash "$m\c512-ffn.hsaco").Hash;deep_sha256=(Get-FileHash "$m\c512-deep.hsaco").Hash}
[IO.File]::WriteAllText("$m\build-manifest.json",($manifest|ConvertTo-Json),(New-Object Text.UTF8Encoding($false)))
$manifest|ConvertTo-Json
