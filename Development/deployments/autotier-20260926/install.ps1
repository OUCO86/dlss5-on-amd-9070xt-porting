param([string]$RestoreBackup='')
# Auto-tier add-on (cd0fea6: inputs <=10% beyond a tier fit down into it) for Stellar Blade, flags NETWORK_HEIGHT -> auto.
# Replaces only dlss5-amd.addon64 (and its _storage_ copy if present); modules unchanged (wave-owned prod8+2).
$ErrorActionPreference='Stop'
$g='C:\Program Files (x86)\Steam\steamapps\common\StellarBlade\SB\Binaries\Win64'
$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$flags="$g\DLSS5-AMD\native-game-flags.txt"
$new='F71F38A3FBE36328F44E71D0C41993CF19DEC38B6B1A1D067B9F50775184B58F'
$prev='3E3CA57A079B607405227A7B3B5B1C72B71AE0416438928E69BC3B65808E67A8'
$targets=@('dlss5-amd.addon64')+@(if(Test-Path "$g\_storage_\dlss5-amd.addon64"){'_storage_\dlss5-amd.addon64'})
if(Get-Process SB-Win64-Shipping -ErrorAction SilentlyContinue){throw 'game running'}
if($RestoreBackup){foreach($t in $targets){Copy-Item "$RestoreBackup\$($t -replace '\\','_')" "$g\$t" -Force};Copy-Item "$RestoreBackup\native-game-flags.txt" $flags -Force;"RESTORED $RestoreBackup";exit}
if((Get-FileHash "$root\dlss5-amd.addon64").Hash -ne $new){throw 'candidate hash mismatch'}
foreach($t in $targets){if((Get-FileHash "$g\$t").Hash -ne $prev){throw "installed $t is not the wave-owned add-on $prev"}}
$dxgi=(Get-FileHash "$g\dxgi.dll").Hash
$b="$root\backups\$(Get-Date -Format yyyyMMdd-HHmmss)";New-Item -ItemType Directory -Force $b|Out-Null
foreach($t in $targets){Copy-Item "$g\$t" "$b\$($t -replace '\\','_')"};Copy-Item $flags "$b\native-game-flags.txt"
foreach($t in $targets){Copy-Item "$root\dlss5-amd.addon64" "$g\$t" -Force;if((Get-FileHash "$g\$t").Hash -ne $new){throw "verify failed $t"}}
$lines=@(Get-Content $flags)|ForEach-Object{if($_ -match '^\s*DLSS5_NETWORK_HEIGHT\s*='){'DLSS5_NETWORK_HEIGHT=auto'}else{$_}};[IO.File]::WriteAllLines($flags,$lines)
if((Get-FileHash "$g\dxgi.dll").Hash -ne $dxgi){throw 'dxgi changed unexpectedly'}
"INSTALLED $($targets.Count) add-on file(s) f71f38a3 + NETWORK_HEIGHT=auto; BACKUP=$b"
