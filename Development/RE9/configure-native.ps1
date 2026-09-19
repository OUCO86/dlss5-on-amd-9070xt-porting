param([ValidateSet('Native1080')][string]$Mode='Native1080')
$ErrorActionPreference='Stop'
$g='C:\Program Files (x86)\Steam\steamapps\common\RESIDENT EVIL requiem BIOHAZARD requiem'
if(Get-Process re9 -ErrorAction SilentlyContinue){throw 'Exit RE9 before changing its saved graphics settings'}
$p="$g\config.ini";$b='D:\DLSSNR-Lab\re9-opti\before-native-config.ini'
if(!(Test-Path $b)){Copy-Item $p $b}
$f=Get-Content $p
$f=$f -replace '^Resolution=.*$','Resolution=1920x1080' -replace '^UpscalingAlgorithm=.*$','UpscalingAlgorithm=None' -replace '^WindowMode=.*$','WindowMode=Normal' -replace '^NormalWindowResolution=.*$','NormalWindowResolution=(1920.000000,1080.000000)'
$f|Set-Content $p -Encoding ASCII
$f|Where-Object{$_ -match '^(Resolution|UpscalingAlgorithm)='}
