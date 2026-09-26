param([string]$RestoreBackup='',[ValidateSet('stellar','cyberpunk')][string]$Game='stellar')
# Opt-in ViT projection 64-column kernel (DLSS5_HIP_VIT_PROJ_N64=1) on top of the installed wave-owned + C512 M32 + auto-tier.
# Adds vit-wide-deep.hsaco for gfx1200/gfx1201, replaces dlss5-amd.addon64 (+ _storage_ copy), sets the flag.
# -RestoreBackup <dir> undoes everything. PREPARED, NOT EXECUTED (2026-09-26). Run with the game closed, from
# D:\DLSSNR-Lab\vit-proj-n64-20260926 (this folder + payload\).
$ErrorActionPreference='Stop'
$g=if($Game -eq 'cyberpunk'){'C:\Program Files (x86)\Steam\steamapps\common\Cyberpunk 2077\bin\x64'}else{'C:\Program Files (x86)\Steam\steamapps\common\StellarBlade\SB\Binaries\Win64'}
$proc=if($Game -eq 'cyberpunk'){'Cyberpunk2077'}else{'SB-Win64-Shipping'}
$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$flags="$g\DLSS5-AMD\native-game-flags.txt";$hipDir="$g\DLSS5-AMD\native-game-tiled-assets\HIP"
$addonNew='106FF3D065E2848C3D59A4445293ADD79368B0DB6C4EF3EB16D89BA62CE6BE6F'
$addonKnown=@('3D8295DBC8AA4D8C2613E81A008273D9D211602C087FB8E3D25713948E978A38',$addonNew)
$modules=@{'gfx1200\vit-wide-deep.hsaco'='20AD91A849B01F7204A7469CCD43D9C02E94ED17A96EE45EF8D57AAFACFA86AD';'gfx1201\vit-wide-deep.hsaco'='AD8642DAA421E1100E6801FE37D04E6ECD9D6359C39DE42F91FFF865E751FBC9'}
$addons=@('dlss5-amd.addon64')+@(if(Test-Path "$g\_storage_\dlss5-amd.addon64"){'_storage_\dlss5-amd.addon64'})
if(Get-Process $proc -ErrorAction SilentlyContinue){throw "$Game running"}
if($RestoreBackup){
 foreach($t in $addons){Copy-Item "$RestoreBackup\$($t -replace '\\','_')" "$g\$t" -Force}
 foreach($m in $modules.Keys){Remove-Item "$hipDir\$m" -ErrorAction SilentlyContinue}
 Copy-Item "$RestoreBackup\native-game-flags.txt" $flags -Force;"RESTORED $RestoreBackup";exit
}
foreach($need in 'DLSS5_HIP_WAVE_OWNED','DLSS5_HIP_C512_M32'){if(!(Get-Content $flags|Where-Object{$_ -match "^\s*$need\s*=\s*1\s*$"})){throw "$need is not enabled on this install"}}
foreach($t in $addons){if((Get-FileHash "$g\$t").Hash -notin $addonKnown){throw "unrecognized installed add-on $t"}}
if((Get-FileHash "$root\dlss5-amd.addon64").Hash -ne $addonNew){throw 'candidate add-on hash mismatch'}
foreach($m in $modules.Keys){if((Get-FileHash "$root\payload\$m").Hash -ne $modules[$m]){throw "payload hash mismatch $m"};if(!(Test-Path (Split-Path "$hipDir\$m"))){throw "missing module dir for $m"}}
$dxgi=(Get-FileHash "$g\dxgi.dll").Hash
$b="$root\backups\$Game-$(Get-Date -Format yyyyMMdd-HHmmss)";New-Item -ItemType Directory -Force $b|Out-Null
foreach($t in $addons){Copy-Item "$g\$t" "$b\$($t -replace '\\','_')"};Copy-Item $flags "$b\native-game-flags.txt"
try{
 foreach($t in $addons){Copy-Item "$root\dlss5-amd.addon64" "$g\$t" -Force;if((Get-FileHash "$g\$t").Hash -ne $addonNew){throw "verify failed $t"}}
 foreach($m in $modules.Keys){Copy-Item "$root\payload\$m" "$hipDir\$m" -Force;if((Get-FileHash "$hipDir\$m").Hash -ne $modules[$m]){throw "verify failed $m"}}
 $lines=@(Get-Content $flags)|Where-Object{$_ -notmatch '^\s*DLSS5_HIP_VIT_PROJ_N64\s*='};[IO.File]::WriteAllLines($flags,$lines+@('DLSS5_HIP_VIT_PROJ_N64=1'))
 if((Get-FileHash "$g\dxgi.dll").Hash -ne $dxgi){throw 'dxgi changed unexpectedly'}
 "INSTALLED add-on 106ff3d0 + 2 vit-wide-deep modules + DLSS5_HIP_VIT_PROJ_N64=1; BACKUP=$b"
}catch{foreach($t in $addons){Copy-Item "$b\$($t -replace '\\','_')" "$g\$t" -Force};foreach($m in $modules.Keys){Remove-Item "$hipDir\$m" -ErrorAction SilentlyContinue};Copy-Item "$b\native-game-flags.txt" $flags -Force;throw}
