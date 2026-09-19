param([ValidateSet('Install','Update','Restore')][string]$Action='Install')
$ErrorActionPreference='Stop'
$g='C:\Program Files (x86)\Steam\steamapps\common\RESIDENT EVIL requiem BIOHAZARD requiem'
$r='D:\DLSSNR-Lab\re9-opti';$b="$r\before-observer"
if(Get-Process re9,LOP-Win64-Shipping,SB-Win64-Shipping,Magpie -ErrorAction SilentlyContinue){throw 'Exit games/Magpie before this diagnostic'}
$src="$r\native-re9-observer.addon64";$sha='2bc1ee441c117c349bd30364789f8e23dc7f61d1354e010622fb227060f944e3'
if((Get-FileHash $src).Hash -ne $sha){throw 'Observer checksum mismatch'}
$targets=@("$g\re9-ffx-observer.addon64","$g\_storage_\re9-ffx-observer.addon64")
$known=@($sha,'54aa65b673443fd509ca8699a08e90487feb1eba7d845732faacb06d475046ae')
if($Action -in 'Update','Restore'){
 foreach($dst in $targets){if((Test-Path $dst) -and (Get-FileHash $dst).Hash -notin $known){throw 'Unknown observer binary'}}
 if($Action -eq 'Restore'){foreach($dst in $targets){if(Test-Path $dst){Remove-Item $dst}};'OBSERVER_REMOVED; original disabled-addon state retained';exit}
 foreach($dst in $targets){if(Test-Path $dst){$leaf=if($dst.Contains('\_storage_\')){'storage-observer.addon64'}else{'root-observer.addon64'};if(!(Test-Path "$b\$leaf")){Copy-Item $dst "$b\$leaf"};Copy-Item $src $dst -Force;if((Get-FileHash $dst).Hash -ne $sha){throw 'Update checksum mismatch'}}}
 'OBSERVER_UPDATED: direct upscaler provider';exit
}

if(Get-ChildItem $g -Recurse -File -Filter *.addon64|Where-Object{$_.FullName -notmatch '\\reframework\\'}){throw 'Active addon exists; inspect before proceeding'}
if(Test-Path $b){throw 'Backup exists'}
New-Item -ItemType Directory -Force $b|Out-Null
Copy-Item "$g\DLSS5-AMD\native-game-flags.txt" "$b\native-game-flags.txt"
Get-ChildItem "$g\*.addon64*"|Select-Object Name,Length|ConvertTo-Json|Set-Content "$b\previous-addons.json"
Copy-Item $src "$g\re9-ffx-observer.addon64"
if((Get-FileHash "$g\re9-ffx-observer.addon64").Hash -ne $sha){throw 'Installed checksum mismatch'}
'OBSERVER_INSTALLED: original FFX forwarded, no DLSS5 processing; previous DLSS5 remains .off'
