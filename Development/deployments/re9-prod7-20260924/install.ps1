param([switch]$Restore)
# RE9 (OptiScaler-REFramework route): replace the HIP kernel modules under DLSS5-AMD\native-game-tiled-assets\HIP\{gfx1200,gfx1201}
# with the prod7 set (prod6 + mh_fast full-line stores). Only files already present in the target are replaced; SHA256SUMS lists
# names only (LmxxfNrRuntime::ValidateModuleSet checks presence, not hashes). -Restore puts the backup back.
$ErrorActionPreference='Stop'
$g='C:\Program Files (x86)\Steam\steamapps\common\RESIDENT EVIL requiem BIOHAZARD requiem'
$hip="$g\DLSS5-AMD\native-game-tiled-assets\HIP";$l='D:\DLSSNR-Lab\re9-prod7-20260924';$b="$l\backup"
if(Get-Process re9 -ErrorAction SilentlyContinue){throw 'RE9 running; close it first'}
$sets=@{gfx1201='D:\DLSSNR-Lab\hip-backend\network-fixed-shapes\prod7-modules';gfx1200='D:\DLSSNR-Lab\hip-backend\network-fixed-shapes\prod7-gfx1200'}
if($Restore){foreach($arch in $sets.Keys){Copy-Item "$b\$arch\*.hsaco" "$hip\$arch\" -Force};"RESTORED from $b";exit}
$n=0
foreach($arch in $sets.Keys){
 New-Item -ItemType Directory -Force "$b\$arch"|Out-Null
 foreach($f in Get-ChildItem "$hip\$arch" -Filter *.hsaco){
  $src=Join-Path $sets[$arch] $f.Name
  if(!(Test-Path $src)){"skip (not in prod7 set): $arch\$($f.Name)";continue}
  if((Get-FileHash $src).Hash -eq (Get-FileHash $f.FullName).Hash){continue}
  if(!(Test-Path "$b\$arch\$($f.Name)")){Copy-Item $f.FullName "$b\$arch\$($f.Name)"}
  Copy-Item $src $f.FullName -Force;$n++
 }
}
"INSTALLED prod7: $n modules replaced; BACKUP=$b"
foreach($arch in $sets.Keys){"$arch mh_fast " + (Get-FileHash "$hip\$arch\multihead-fast-padded-wave-packed.hsaco").Hash.ToLower().Substring(0,16)}
