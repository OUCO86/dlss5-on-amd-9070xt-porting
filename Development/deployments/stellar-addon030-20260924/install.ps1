param([switch]$Restore)
# DLSS5_FIT_LARGE test build (issue #6): replaces the add-on DLL and adds DLSS5_FIT_LARGE=1 to native-game-flags.txt.
# -Restore puts back the backed-up DLL and flags file.
$ErrorActionPreference='Stop'
$g='C:\Program Files (x86)\Steam\steamapps\common\StellarBlade\SB\Binaries\Win64'
$l='D:\DLSSNR-Lab\stellar-addon030-20260924'
if(Get-Process SB-Win64-Shipping -ErrorAction SilentlyContinue){throw 'Stellar Blade running; close it first'}
$dll="$g\dlss5-amd.addon64";$flags="$g\DLSS5-AMD\native-game-flags.txt";$b="$l\backup"
if($Restore){Copy-Item "$b\dlss5-amd.addon64" $dll -Force;Copy-Item "$b\native-game-flags.txt" $flags -Force;"RESTORED from $b";exit}
New-Item -ItemType Directory -Force $b|Out-Null
if(!(Test-Path "$b\dlss5-amd.addon64")){Copy-Item $dll "$b\dlss5-amd.addon64";Copy-Item $flags "$b\native-game-flags.txt"}
Copy-Item "$l\dlss5-amd.addon64" $dll -Force
$lines=@(Get-Content $flags)|Where-Object{$_ -notmatch '^DLSS5_FIT_LARGE='}
[IO.File]::WriteAllLines($flags,$lines+@('DLSS5_FIT_LARGE=1'))
"INSTALLED fit-large add-on (sha256 $((Get-FileHash $dll).Hash.Substring(0,16))...) + DLSS5_FIT_LARGE=1; BACKUP=$b"
