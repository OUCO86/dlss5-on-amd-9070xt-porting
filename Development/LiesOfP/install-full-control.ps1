$ErrorActionPreference='Stop'
$g='C:\Program Files (x86)\Steam\steamapps\common\Lies of P\LiesofP\Binaries\Win64'
if(Get-Process LOP-Win64-Shipping -ErrorAction SilentlyContinue){throw 'Exit Lies of P'}
$src='D:\DLSSNR-Lab\hip-backend\full-control.addon64';$expected='bccbe270703c1e5d4ea771a5d27afaf5600f8ea266c7467576e80b7898f992e8'
if((Get-FileHash $src).Hash -ne $expected){throw 'Candidate mismatch'}
if((Get-FileHash "$g\DLSS5-AMD\native-game-tiled-assets\HIP\gfx1201\deep_fast-packed.hsaco").Hash -ne '9fdd8a0207a3097d5df7c6bf9ae9298a905e9039c5944030d072c9f9a96eb231'){throw 'Wrong module ABI'}
$b='D:\DLSSNR-Lab\liesofp-full-control-backups\'+(Get-Date -Format 'yyyyMMdd-HHmmss-fff');New-Item -ItemType Directory -Force $b|Out-Null
Copy-Item "$g\dlss5-amd.addon64" "$b\dlss5-amd.addon64"
$f="$g\DLSS5-AMD\native-game-flags.txt";Copy-Item $f "$b\native-game-flags.txt"
$lines=@(Get-Content $f|Where-Object{$_ -notmatch '^DLSS5_(SKIP_BLOCKS|VIT_ADAPTIVE|VIT_REUSE_HOTKEY)='})+@('DLSS5_SKIP_BLOCKS=','DLSS5_VIT_ADAPTIVE=0','DLSS5_VIT_REUSE_HOTKEY=0')
try{Copy-Item $src "$g\dlss5-amd.addon64" -Force;[IO.File]::WriteAllLines($f,$lines,(New-Object Text.UTF8Encoding($false)));if((Get-FileHash "$g\dlss5-amd.addon64").Hash -ne $expected){throw 'Installed hash mismatch'}}catch{Copy-Item "$b\dlss5-amd.addon64" "$g\dlss5-amd.addon64" -Force;Copy-Item "$b\native-game-flags.txt" $f -Force;throw}
Write-Output "INSTALLED full-network comparison; BACKUP=$b"
