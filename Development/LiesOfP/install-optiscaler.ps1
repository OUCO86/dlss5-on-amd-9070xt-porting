param([ValidateSet('Install','Restore')][string]$Action='Install',[string]$Backup='')
$ErrorActionPreference='Stop'
$game='C:\Program Files (x86)\Steam\steamapps\common\Lies of P\LiesofP\Binaries\Win64'
$source='D:\給網友打包\OptiScaler-DLSS5-AMD-0.27'
function Closed {if(Get-Process LOP-Win64-Shipping -ErrorAction SilentlyContinue){throw 'Exit Lies of P before replacing files'}}
Closed
if($Action -eq 'Restore'){
 if(!$Backup){throw 'Specify the install backup directory'}
 $rows=Get-Content "$Backup\inventory.json" -Raw|ConvertFrom-Json
 foreach($row in $rows){$target=Join-Path $game $row.rel;if($row.existed){Copy-Item (Join-Path "$Backup\files" $row.rel) $target -Force}else{Remove-Item $target -Force -ErrorAction SilentlyContinue}}
 Write-Output 'Restored original files; empty added directories may remain.';exit
}
if(!(Test-Path "$game\LOP-Win64-Shipping.exe")){throw 'Executable not found'}
$items=@()
foreach($line in Get-Content "$source\SHA256SUMS.txt"){
 if($line -notmatch '^([0-9a-fA-F]{64})\s+(.+)$'){throw 'Bad package inventory'}
 $hash=$matches[1];$rel=$matches[2].Replace('/','\')
 if([IO.Path]::IsPathRooted($rel) -or ($rel.Split('\') -contains '..')){throw 'Unsafe package path'}
 if((Get-FileHash (Join-Path $source $rel)).Hash -ne $hash){throw "Package mismatch $rel"}
 $target=Join-Path $game $rel
 $items+=[pscustomobject]@{rel=$rel;installed_sha=$hash;existed=(Test-Path $target);original_sha=$(if(Test-Path $target){(Get-FileHash $target).Hash}else{''})}
}
$Backup='D:\DLSSNR-Lab\liesofp-backups\'+(Get-Date -Format 'yyyyMMdd-HHmmss-fff')
New-Item -ItemType Directory -Force "$Backup\files"|Out-Null
foreach($i in $items){if($i.existed){$p=Join-Path "$Backup\files" $i.rel;New-Item -ItemType Directory -Force (Split-Path $p)|Out-Null;Copy-Item (Join-Path $game $i.rel) $p;if((Get-FileHash $p).Hash -ne $i.original_sha){throw 'Backup hash mismatch'}}}
$items|ConvertTo-Json -Depth 4|Set-Content "$Backup\inventory.json" -Encoding UTF8
Closed
try{
 foreach($i in $items){$target=Join-Path $game $i.rel;New-Item -ItemType Directory -Force (Split-Path $target)|Out-Null;Copy-Item (Join-Path $source $i.rel) $target -Force}
 foreach($i in $items){if((Get-FileHash (Join-Path $game $i.rel)).Hash -ne $i.installed_sha){throw "Installed hash mismatch $($i.rel)"}}
}catch{foreach($i in $items){$target=Join-Path $game $i.rel;if($i.existed){Copy-Item (Join-Path "$Backup\files" $i.rel) $target -Force}else{Remove-Item $target -Force -ErrorAction SilentlyContinue}};throw}
[pscustomobject]@{target=$game;backup=$Backup;files=$items.Count;replaced_count=@($items|Where-Object existed).Count}|ConvertTo-Json
