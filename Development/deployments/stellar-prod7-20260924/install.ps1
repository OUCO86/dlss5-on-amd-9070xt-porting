param([string]$RestoreBackup='')
$ErrorActionPreference='Stop'
$g='C:\Program Files (x86)\Steam\steamapps\common\StellarBlade\SB\Binaries\Win64'
$l='D:\DLSSNR-Lab\stellar-prod7-20260924'
function Closed {if(Get-Process SB-Win64-Shipping -ErrorAction SilentlyContinue){throw 'Stellar Blade running; no DLL replacement allowed'}}
function Restore($b){Closed;$m=Get-Content "$b\installed.json" -Raw|ConvertFrom-Json;foreach($i in $m.items){if($i.existed){Copy-Item (Join-Path $b $i.target) (Join-Path $g $i.target) -Force}else{Remove-Item (Join-Path $g $i.target) -ErrorAction SilentlyContinue}};"RESTORED $b"}
Closed
if($RestoreBackup){Restore $RestoreBackup;exit}
$items=Get-Content "$l\payload.json" -Raw|ConvertFrom-Json
if(Test-Path "$g\_storage_\dlss5-amd.addon64"){$i=$items[0];$items += [pscustomobject]@{source=$i.source;target='_storage_/dlss5-amd.addon64';sha256=$i.sha256}}
foreach($i in $items){if((Get-FileHash $i.source).Hash -ne $i.sha256){throw "Candidate hash mismatch: $($i.source)"}}
$unchanged=@{};foreach($f in @('dxgi.dll','OptiScaler.ini','DLSS5-AMD/native-game-flags.txt')){$unchanged[$f]=(Get-FileHash (Join-Path $g $f)).Hash}
$b="$l\backups\$(Get-Date -Format yyyyMMdd-HHmmss)"
$records=@(foreach($i in $items){$p=Join-Path $g $i.target;$exist=Test-Path $p;$old=$null;if($exist){$old=(Get-FileHash $p).Hash;$dst=Join-Path $b $i.target;New-Item -ItemType Directory (Split-Path $dst) -Force|Out-Null;Copy-Item $p $dst;if((Get-FileHash $dst).Hash -ne $old){throw 'Backup hash mismatch'}};[pscustomobject]@{target=$i.target;source=$i.source;existed=$exist;before=$old;after=$i.sha256}})
$m=[pscustomobject]@{source_commit='prod7-20260924';backup=$b;items=$records;unchanged=$unchanged}
$m|ConvertTo-Json -Depth 6|Set-Content "$b\installed.json"
try{
 Closed
 foreach($i in $items){Copy-Item $i.source (Join-Path $g $i.target) -Force;if((Get-FileHash (Join-Path $g $i.target)).Hash -ne $i.sha256){throw 'Installed payload mismatch'}}
 foreach($f in $unchanged.Keys){if((Get-FileHash (Join-Path $g $f)).Hash -ne $unchanged[$f]){throw "Unexpected configuration/host change $f"}}
 $m|ConvertTo-Json -Depth 6|Set-Content "$l\installed.json"
 "INSTALLED $($items.Count) verified files; host/INI/flags unchanged; BACKUP=$b"
}catch{Restore $b;throw}
