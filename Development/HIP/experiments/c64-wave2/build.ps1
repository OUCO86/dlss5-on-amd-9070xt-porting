param([ValidateSet('row','frag')][string]$Layout='row',[switch]$DeferQ,[switch]$Launder,[switch]$Schedule,[switch]$RollQuery,[ValidateSet(1,2,4,8)][int]$HiddenTiles=1)
$ErrorActionPreference='Stop'
$r='D:\DLSSNR-Lab\hip-backend';$d=Split-Path -Parent $MyInvocation.MyCommand.Path
& "$r\check-idle.ps1"
$suffix=if($DeferQ){'-defer'}else{''}
if($Launder){$suffix+='-launder'}
if($Schedule){$suffix+='-sched'}
if($RollQuery){$suffix+='-roll'}
if($HiddenTiles -ne 1){$suffix+="-ht$HiddenTiles"}
$m="$d\modules-$Layout$suffix";New-Item -ItemType Directory -Force $m | Out-Null
Copy-Item "$r\network-fixed-shapes\prod8-modules\*.hsaco" $m
$prefix=@()
if($Layout -eq 'frag'){$prefix+='#define W2_FRAGMENT_WEIGHTS 1'}
if($DeferQ){$prefix+='#define W2_DEFER_Q 1'}
if($Launder){$prefix+='#define W2_LAUNDER_QKV 1'}
if($Schedule){$prefix+='#define W2_SCHED_FENCE 1'}
if($RollQuery){$prefix+='#define W2_ROLL_QUERY 1'}
$prefix+="#define W2_HIDDEN_TILES $HiddenTiles"
$source="$m\build.hip"
[IO.File]::WriteAllText($source,($prefix -join "`n")+"`n"+[IO.File]::ReadAllText("$d\kernel.hip"),(New-Object Text.UTF8Encoding($false)))
& 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$m\c64-wave2.hsaco" $source comgr gfx1201
if($LASTEXITCODE){throw 'Compile failed'}
Get-FileHash "$m\c64-wave2.hsaco"
$manifest=@{layout=$Layout;defer_q=[bool]$DeferQ;launder_qkv=[bool]$Launder;schedule_fence=[bool]$Schedule;roll_query=[bool]$RollQuery;hidden_tiles=$HiddenTiles;source_sha256=(Get-FileHash $source).Hash;module_sha256=(Get-FileHash "$m\c64-wave2.hsaco").Hash}
[IO.File]::WriteAllText("$m\build-manifest.json",($manifest|ConvertTo-Json),(New-Object Text.UTF8Encoding($false)))
