param([string]$Diagnostic='split-original',[string]$RestoreBackup='')
$ErrorActionPreference='Stop'
$g='C:\Program Files (x86)\Steam\steamapps\common\RESIDENT EVIL requiem BIOHAZARD requiem'
$lab='D:\DLSSNR-Lab\re9-presr'
if(Get-Process re9 -ErrorAction SilentlyContinue){throw 'Game still running; no files changed'}
if($RestoreBackup){
 $m=Get-Content "$RestoreBackup\manifest.json" -Raw|ConvertFrom-Json
 foreach($f in $m.files){$p=Join-Path $g $f.name;if($f.existed){Copy-Item (Join-Path $RestoreBackup $f.name) $p -Force}else{if(Test-Path $p){Remove-Item $p}}}
 "RESTORED $RestoreBackup";exit
}
$names=@('config.ini','OptiScaler.ini','dxgi.dll','LmxxfNrRuntime.dll','re9-present.addon64','_storage_\OptiScaler.ini','_storage_\dxgi.dll','_storage_\LmxxfNrRuntime.dll','_storage_\re9-present.addon64','DLSS5-AMD\native-game-tiled-assets\HIP\SHA256SUMS')
$names+=@('DLSS5-AMD\native-game-tiled-assets\native_codec_encode.hlsl','DLSS5-AMD\native-game-tiled-assets\native_codec_decode.hlsl')
$b="$lab\backups\$(Get-Date -Format yyyyMMdd-HHmmss-fff)"
New-Item -ItemType Directory $b -Force|Out-Null
$files=@(foreach($n in $names){$exists=Test-Path "$g\$n";if($exists){$dest=Join-Path $b $n;New-Item -ItemType Directory (Split-Path $dest) -Force|Out-Null;Copy-Item "$g\$n" $dest};[pscustomobject]@{name=$n;existed=$exists}})
[pscustomobject]@{files=$files;diagnostic=$Diagnostic}|ConvertTo-Json -Depth 4|Set-Content "$b\manifest.json"
Set-Content "$lab\last-backup.txt" $b
foreach($d in @($g,"$g\_storage_")){
 Copy-Item "$lab\bin\OptiScaler.dll" "$d\dxgi.dll" -Force
 Copy-Item "$lab\LmxxfNrRuntime.dll" "$d\LmxxfNrRuntime.dll" -Force
 if(Test-Path "$d\re9-present.addon64"){Remove-Item "$d\re9-present.addon64"}
}
foreach($n in @('native_codec_encode.hlsl','native_codec_decode.hlsl')){Copy-Item "$lab\shaders\$n" "$g\DLSS5-AMD\native-game-tiled-assets\$n" -Force}
$ini=Get-Content "$g\OptiScaler.ini" -Raw
$ini=$ini -replace '(?ms)^\[DlssNr\].*?(?=^\[|\z)',''
$ini=$ini -replace '(?m)^LoadReshade=.*$','LoadReshade=false'
$ini+="`r`n[DlssNr]`r`nEnabled=true`r`nRunBeforeSR=true`r`nNrBackend=lmxxf`r`nLmxxfDiagnostic=$Diagnostic`r`nAmdEveryFrame=true`r`nTransferStrength=1.0`r`nColourStrength=1.0`r`nToggleKey=117`r`n"
[IO.File]::WriteAllText("$g\OptiScaler.ini",$ini)
Copy-Item "$g\OptiScaler.ini" "$g\_storage_\OptiScaler.ini" -Force
$config=Get-Content "$g\config.ini" -Raw
$config=$config -replace '(?m)^Resolution=.*$','Resolution=2560x1440'
$config=$config -replace '(?m)^WindowMode=.*$','WindowMode=Borderless'
$config=$config -replace '(?m)^FrameGeneration=.*$','FrameGeneration=Off'
[IO.File]::WriteAllText("$g\config.ini",$config)
$hip="$g\DLSS5-AMD\native-game-tiled-assets\HIP"
$hashes=Get-ChildItem "$hip\*.hsaco"|Sort-Object Name|ForEach-Object{(Get-FileHash $_.FullName).Hash.ToLower()+'  '+$_.Name}
[IO.File]::WriteAllLines("$hip\SHA256SUMS",[string[]]$hashes)
"BACKUP $b";Get-FileHash "$g\dxgi.dll","$g\LmxxfNrRuntime.dll"
