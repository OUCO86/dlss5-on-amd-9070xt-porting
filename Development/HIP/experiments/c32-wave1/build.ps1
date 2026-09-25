param([switch]$Launder,[switch]$RollHidden,[switch]$QkvFence,[switch]$Wgp,[switch]$RollWindow)
$ErrorActionPreference='Stop';$d=Split-Path -Parent $MyInvocation.MyCommand.Path;$r='D:\DLSSNR-Lab\hip-backend'
& "$r\check-idle.ps1"
$suffix=if($Launder){'-launder'}else{''}
if($RollHidden){$suffix+='-rollh'}
if($QkvFence){$suffix+='-qf'}
if($Wgp){$suffix+='-wgp'}
if($RollWindow){$suffix+='-rw'}
$m="$d\modules$suffix"
New-Item -ItemType Directory -Force "$m" | Out-Null
Copy-Item "$r\network-fixed-shapes\prod8-modules\*.hsaco" "$m"
$source="$m\build.hip"
$prefix=if($Launder){"#define CW_LAUNDER 1`n"}else{''}
if($RollHidden){$prefix+="#define CW_ROLL_HIDDEN 1`n"}
if($QkvFence){$prefix+="#define CW_QKV_FENCE 1`n"}
if($Wgp){$prefix+="#define HIP_C32_CU_MODE 0`n"}
if($RollWindow){$prefix+="#define CW_ROLL_WINDOW 1`n"}
[IO.File]::WriteAllText($source,$prefix+[IO.File]::ReadAllText("$d\kernel.hip"),(New-Object Text.UTF8Encoding($false)))
& 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe'  "$m\c32-wave1.hsaco" $source comgr gfx1201
if($LASTEXITCODE){throw 'compile failed'}
Get-FileHash "$m\c32-wave1.hsaco"
$manifest=@{launder=[bool]$Launder;roll_hidden=[bool]$RollHidden;qkv_fence=[bool]$QkvFence;wgp=[bool]$Wgp;roll_window=[bool]$RollWindow;source_sha256=(Get-FileHash $source).Hash;module_sha256=(Get-FileHash "$m\c32-wave1.hsaco").Hash}
[IO.File]::WriteAllText("$m\build-manifest.json",($manifest|ConvertTo-Json),(New-Object Text.UTF8Encoding($false)))
