param([string]$RestoreBackup='',[ValidateSet('stellar','cyberpunk')][string]$Game='stellar')
# Opt-in C512 32-token kernels (DLSS5_HIP_C512_M32=1) on top of wave-owned + auto-tier. Adds c512-m32-mh/deep modules for
# gfx1200/gfx1201, replaces dlss5-amd.addon64 (+ _storage_ copy), sets the flag. -RestoreBackup <dir> undoes everything.
# PREPARED, NOT EXECUTED (2026-09-26). Run with the game closed, from D:\DLSSNR-Lab\c512-m32-20260926 (this folder + payload\).
$ErrorActionPreference='Stop'
$g=if($Game -eq 'cyberpunk'){'C:\Program Files (x86)\Steam\steamapps\common\Cyberpunk 2077\bin\x64'}else{'C:\Program Files (x86)\Steam\steamapps\common\StellarBlade\SB\Binaries\Win64'}
$proc=if($Game -eq 'cyberpunk'){'Cyberpunk2077'}else{'SB-Win64-Shipping'}
$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$flags="$g\DLSS5-AMD\native-game-flags.txt";$hipDir="$g\DLSS5-AMD\native-game-tiled-assets\HIP"
$addonNew='3D8295DBC8AA4D8C2613E81A008273D9D211602C087FB8E3D25713948E978A38'
$addonKnown=@('F71F38A3FBE36328F44E71D0C41993CF19DEC38B6B1A1D067B9F50775184B58F','3E3CA57A079B607405227A7B3B5B1C72B71AE0416438928E69BC3B65808E67A8',$addonNew)
$modules=@{'gfx1200\c512-m32-mh.hsaco'='8BA6908BDDA0C44A063314FE79F65AE811B753986F2784D4EAC60D519EF64CC7';'gfx1200\c512-m32-deep.hsaco'='6DA5DD7C7DB229B2A756649E0C8227D625CA474312E790CDC2E0FFEB86543058';'gfx1201\c512-m32-mh.hsaco'='6733469AA5E95E19BBB97FE15090C300140414D8E54452EBD024976125922127';'gfx1201\c512-m32-deep.hsaco'='93080FD44F55F8F935BAB9DC16C7E7302B914EA26221D683CAE99D00FECF8B7E'}
$addons=@('dlss5-amd.addon64')+@(if(Test-Path "$g\_storage_\dlss5-amd.addon64"){'_storage_\dlss5-amd.addon64'})
if(Get-Process $proc -ErrorAction SilentlyContinue){throw "$Game running"}
if($RestoreBackup){
 foreach($t in $addons){Copy-Item "$RestoreBackup\$($t -replace '\\','_')" "$g\$t" -Force}
 foreach($m in $modules.Keys){Remove-Item "$hipDir\$m" -ErrorAction SilentlyContinue}
 Copy-Item "$RestoreBackup\native-game-flags.txt" $flags -Force;"RESTORED $RestoreBackup";exit
}
if(!(Get-Content $flags|Where-Object{$_ -match '^\s*DLSS5_HIP_WAVE_OWNED\s*=\s*1\s*$'})){throw 'wave-owned is not enabled on this install'}
foreach($t in $addons){if((Get-FileHash "$g\$t").Hash -notin $addonKnown){throw "unrecognized installed add-on $t"}}
if((Get-FileHash "$root\dlss5-amd.addon64").Hash -ne $addonNew){throw 'candidate add-on hash mismatch'}
foreach($m in $modules.Keys){if((Get-FileHash "$root\payload\$m").Hash -ne $modules[$m]){throw "payload hash mismatch $m"};if(!(Test-Path (Split-Path "$hipDir\$m"))){throw "missing module dir for $m"}}
$dxgi=(Get-FileHash "$g\dxgi.dll").Hash
$b="$root\backups\$Game-$(Get-Date -Format yyyyMMdd-HHmmss)";New-Item -ItemType Directory -Force $b|Out-Null
foreach($t in $addons){Copy-Item "$g\$t" "$b\$($t -replace '\\','_')"};Copy-Item $flags "$b\native-game-flags.txt"
try{
 foreach($t in $addons){Copy-Item "$root\dlss5-amd.addon64" "$g\$t" -Force;if((Get-FileHash "$g\$t").Hash -ne $addonNew){throw "verify failed $t"}}
 foreach($m in $modules.Keys){Copy-Item "$root\payload\$m" "$hipDir\$m" -Force;if((Get-FileHash "$hipDir\$m").Hash -ne $modules[$m]){throw "verify failed $m"}}
 $lines=@(Get-Content $flags)|Where-Object{$_ -notmatch '^\s*DLSS5_HIP_C512_M32\s*='};[IO.File]::WriteAllLines($flags,$lines+@('DLSS5_HIP_C512_M32=1'))
 if((Get-FileHash "$g\dxgi.dll").Hash -ne $dxgi){throw 'dxgi changed unexpectedly'}
 "INSTALLED add-on 3d8295db + 4 C512 modules + DLSS5_HIP_C512_M32=1; BACKUP=$b"
}catch{foreach($t in $addons){Copy-Item "$b\$($t -replace '\\','_')" "$g\$t" -Force};foreach($m in $modules.Keys){Remove-Item "$hipDir\$m" -ErrorAction SilentlyContinue};Copy-Item "$b\native-game-flags.txt" $flags -Force;throw}
