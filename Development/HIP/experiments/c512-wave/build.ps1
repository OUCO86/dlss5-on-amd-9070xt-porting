# Compile c512-wave.hsaco (gfx1201) next to a copy of the wave-owned production module set.
param([switch]$NoRollQuery,[switch]$NoSchedule,[switch]$RollK,[string]$Label='base')
$ErrorActionPreference='Stop'
$r='D:\DLSSNR-Lab\hip-backend';$d=Split-Path -Parent $MyInvocation.MyCommand.Path
$m="$d\modules-$Label";New-Item -ItemType Directory -Force $m | Out-Null
Copy-Item "$r\wave-owned-production\modules-gfx1201\*.hsaco" $m
$prefix=@("#define W2_ROLL_QUERY $([int](-not $NoRollQuery))","#define W2_SCHED_FENCE $([int](-not $NoSchedule))","#define C5_ROLL_K $([int][bool]$RollK)")
$source="$m\build.hip"
[IO.File]::WriteAllText($source,($prefix -join "`n")+"`n"+[IO.File]::ReadAllText("$d\kernel.hip"),(New-Object Text.UTF8Encoding($false)))
& 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$m\c512-wave.hsaco" $source comgr gfx1201
if($LASTEXITCODE){throw 'Compile failed'}
$manifest=@{label=$Label;roll_query=-not $NoRollQuery;schedule_fence=-not $NoSchedule;roll_k=[bool]$RollK;source_sha256=(Get-FileHash $source).Hash;module_sha256=(Get-FileHash "$m\c512-wave.hsaco").Hash}
[IO.File]::WriteAllText("$m\build-manifest.json",($manifest|ConvertTo-Json),(New-Object Text.UTF8Encoding($false)))
$manifest|ConvertTo-Json
