param([switch]$Restore)
# RE9 (OptiScaler-REFramework) DLSS5_FIT_LARGE test: replaces LmxxfNrRuntime.dll (root and _storage_) and adds DLSS5_FIT_LARGE=1
# to DLSS5-AMD\native-game-flags.txt. Host dxgi.dll untouched. -Restore reverts all three.
$ErrorActionPreference='Stop'
$g='C:\Program Files (x86)\Steam\steamapps\common\RESIDENT EVIL requiem BIOHAZARD requiem'
$l='D:\DLSSNR-Lab\re9-fitlarge-20260923';$b="$l\backup"
if(Get-Process re9 -ErrorAction SilentlyContinue){throw 'RE9 running; close it first'}
$targets=@("$g\LmxxfNrRuntime.dll","$g\_storage_\LmxxfNrRuntime.dll")|Where-Object{Test-Path $_}
$flags="$g\DLSS5-AMD\native-game-flags.txt"
if($Restore){foreach($t in $targets){Copy-Item "$b\$(($t -replace '.*\\(_storage_\\)?','$1') -replace '\\','_')" $t -Force};Copy-Item "$b\native-game-flags.txt" $flags -Force;"RESTORED from $b";exit}
New-Item -ItemType Directory -Force $b|Out-Null
foreach($t in $targets){$n=($t -replace '.*\\(_storage_\\)?','$1') -replace '\\','_';if(!(Test-Path "$b\$n")){Copy-Item $t "$b\$n"}}
if(!(Test-Path "$b\native-game-flags.txt")){Copy-Item $flags "$b\native-game-flags.txt"}
foreach($t in $targets){Copy-Item "$l\LmxxfNrRuntime.dll" $t -Force}
$lines=@(Get-Content $flags)|Where-Object{$_ -notmatch '^DLSS5_FIT_LARGE='}
[IO.File]::WriteAllLines($flags,$lines+@('DLSS5_FIT_LARGE=1'))
"INSTALLED runtime $((Get-FileHash "$l\LmxxfNrRuntime.dll").Hash.Substring(0,16))... into $($targets.Count) locations + DLSS5_FIT_LARGE=1; BACKUP=$b"
