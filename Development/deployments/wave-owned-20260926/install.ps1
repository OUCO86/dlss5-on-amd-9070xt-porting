param([string]$RestoreBackup='',[ValidateSet('stellar','cyberpunk')][string]$Game='stellar')
# Opt-in wave-owned modules and add-on, with complete rollback of added files and flags.
# -RestoreBackup <dir> puts back the DLLs, modules and the flags file recorded there.
$ErrorActionPreference='Stop'
$g=if($Game -eq 'cyberpunk'){'C:\Program Files (x86)\Steam\steamapps\common\Cyberpunk 2077\bin\x64'}else{'C:\Program Files (x86)\Steam\steamapps\common\StellarBlade\SB\Binaries\Win64'}
$proc=if($Game -eq 'cyberpunk'){'Cyberpunk2077'}else{'SB-Win64-Shipping'}
$root=Split-Path -Parent $MyInvocation.MyCommand.Path;$l="$root\deploy-$Game";New-Item -ItemType Directory -Force $l|Out-Null
$flagsRel='DLSS5-AMD/native-game-flags.txt'
function Closed {if(Get-Process $proc -ErrorAction SilentlyContinue){throw "$Game running; no DLL replacement allowed"}}
function Restore($b){Closed;$m=Get-Content "$b\installed.json" -Raw|ConvertFrom-Json;foreach($i in $m.items){if($i.existed){Copy-Item (Join-Path $b $i.target) (Join-Path $g $i.target) -Force}else{Remove-Item (Join-Path $g $i.target) -ErrorAction SilentlyContinue}};Copy-Item (Join-Path $b $flagsRel) (Join-Path $g $flagsRel) -Force;"RESTORED $b"}
Closed
if($RestoreBackup){Restore $RestoreBackup;exit}
$moduleOverride=@(Get-Content (Join-Path $g $flagsRel) | Where-Object {$_ -match '^\s*DLSS5_HIP_MODULES\s*=\s*\S'})
if($moduleOverride.Count){throw 'External HIP module directory configured; resolve deployment target first'}
foreach($entry in (Get-Content "$root\baseline.json" -Raw|ConvertFrom-Json)){
 $target=Join-Path $g $entry.target;if(!(Test-Path $target) -or (Get-FileHash $target).Hash -ne $entry.sha256){throw "Installed baseline differs from prod8: $($entry.target)"}
}
$items=Get-Content "$root\payload.json" -Raw|ConvertFrom-Json
$addonCandidate=($items|Where-Object {$_.target -eq 'dlss5-amd.addon64'}).sha256
$addonInstalled=(Get-FileHash (Join-Path $g 'dlss5-amd.addon64')).Hash
if($addonInstalled -notin @('0211A78AC48C48BB0AE8D149F04A8BB8F340FBB75F45967DDF5B9869A40E90EA',$addonCandidate)){throw 'Unrecognized installed add-on; inspect before replacement'}
if(Test-Path "$g\_storage_\dlss5-amd.addon64"){$i=$items|Where-Object{$_.target -eq 'dlss5-amd.addon64'};$items += [pscustomobject]@{source=$i.source;target='_storage_/dlss5-amd.addon64';sha256=$i.sha256}}
foreach($i in $items){if((Get-FileHash $i.source).Hash -ne $i.sha256){throw "Candidate hash mismatch: $($i.source)"}}
$unchanged=@{};foreach($f in @('dxgi.dll','OptiScaler.ini')){$unchanged[$f]=(Get-FileHash (Join-Path $g $f)).Hash}
$b="$l\backups\$(Get-Date -Format yyyyMMdd-HHmmss)"
$records=@(foreach($i in $items){$p=Join-Path $g $i.target;$exist=Test-Path $p;$old=$null;if($exist){$old=(Get-FileHash $p).Hash;$dst=Join-Path $b $i.target;New-Item -ItemType Directory (Split-Path $dst) -Force|Out-Null;Copy-Item $p $dst;if((Get-FileHash $dst).Hash -ne $old){throw 'Backup hash mismatch'}};[pscustomobject]@{target=$i.target;existed=$exist;old=$old;new=$i.sha256}})
$fb=Join-Path $b $flagsRel;New-Item -ItemType Directory (Split-Path $fb) -Force|Out-Null;Copy-Item (Join-Path $g $flagsRel) $fb
$m=[pscustomobject]@{source_recipe='wave-owned-20260926';backup=$b;items=$records;unchanged=$unchanged}
$m|ConvertTo-Json -Depth 6|Set-Content "$b\installed.json"
try{
 Closed
 foreach($i in $items){Copy-Item $i.source (Join-Path $g $i.target) -Force;if((Get-FileHash (Join-Path $g $i.target)).Hash -ne $i.sha256){throw 'Installed payload mismatch'}}
 $fp=Join-Path $g $flagsRel;$lines=@(Get-Content $fp)|Where-Object{$_ -notmatch '^\s*DLSS5_HIP_WAVE_OWNED\s*='};[IO.File]::WriteAllLines($fp,$lines+@('DLSS5_HIP_WAVE_OWNED=1'))
 foreach($f in $unchanged.Keys){if((Get-FileHash (Join-Path $g $f)).Hash -ne $unchanged[$f]){throw "Unexpected host/INI change $f"}}
 $m|ConvertTo-Json -Depth 6|Set-Content "$l\installed.json"
 "INSTALLED $($items.Count) verified files + DLSS5_HIP_WAVE_OWNED=1; host/INI unchanged; BACKUP=$b"
}catch{Restore $b;throw}
