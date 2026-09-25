param([switch]$Restore,[string]$Backup='')
# Forza Horizon 6 (Xbox app, C:\XboxGames): fresh install of the released 0.30 regular OptiScaler package, exactly what a
# player does (extract ALL files beside forzahorizon6.exe). Every file that already existed is backed up; installed.json
# records the whole set so -Restore removes what we added and puts back what we overwrote (game's own FSR dll included).
$ErrorActionPreference='Stop'
$src='D:\給網友打包\OptiScaler-DLSS5-AMD-0.30'
$g='C:\XboxGames\Forza Horizon 6\Content'
$lab='D:\DLSSNR-Lab\forza6-030-20260925';New-Item -ItemType Directory -Force "$lab\backups"|Out-Null
function Closed {if(Get-Process forzahorizon6 -ErrorAction SilentlyContinue){throw 'Forza running; close it first'}}
Closed
if($Restore){
 $b=if($Backup){$Backup}else{(Get-Content "$lab\installed.json" -Raw|ConvertFrom-Json).backup}
 $m=Get-Content "$b\installed.json" -Raw|ConvertFrom-Json
 foreach($i in $m.items){$t=Join-Path $g $i.rel;if($i.existed){Copy-Item (Join-Path $b $i.rel) $t -Force}else{Remove-Item $t -Force -ErrorAction SilentlyContinue}}
 foreach($d in @('DLSS5-AMD','D3D12_Optiscaler','Licenses')){$p=Join-Path $g $d;if((Test-Path $p) -and -not (Get-ChildItem $p -Recurse -File)){Remove-Item $p -Recurse -Force}}
 "RESTORED $b";exit}
if(-not (Test-Path "$g\forzahorizon6.exe")){throw "no forzahorizon6.exe in $g"}
$files=Get-ChildItem $src -Recurse -File
$b="$lab\backups\$(Get-Date -Format yyyyMMdd-HHmmss)";New-Item -ItemType Directory -Force $b|Out-Null
$items=@(foreach($f in $files){$rel=$f.FullName.Substring($src.Length+1);$t=Join-Path $g $rel;$exist=Test-Path $t;$old=$null
 if($exist){$old=(Get-FileHash $t).Hash;$d=Join-Path $b $rel;New-Item -ItemType Directory -Force (Split-Path $d)|Out-Null;Copy-Item $t $d;if((Get-FileHash $d).Hash -ne $old){throw "backup mismatch $rel"}}
 [pscustomobject]@{rel=$rel;existed=$exist;old=$old;new=(Get-FileHash $f.FullName).Hash}})
$m=[pscustomobject]@{package='OptiScaler-DLSS5-AMD-0.30';source=$src;game=$g;backup=$b;items=$items}
$m|ConvertTo-Json -Depth 5|Set-Content "$b\installed.json"
try{
 Closed
 foreach($i in $items){$t=Join-Path $g $i.rel;New-Item -ItemType Directory -Force (Split-Path $t)|Out-Null;Copy-Item (Join-Path $src $i.rel) $t -Force;if((Get-FileHash $t).Hash -ne $i.new){throw "installed mismatch $($i.rel)"}}
 $m|ConvertTo-Json -Depth 5|Set-Content "$lab\installed.json"
 $ow=@($items|Where-Object existed).rel -join ', '
 "INSTALLED $($items.Count) files into $g; overwritten: $ow; BACKUP=$b"
}catch{& $PSCommandPath -Restore -Backup $b;throw}
