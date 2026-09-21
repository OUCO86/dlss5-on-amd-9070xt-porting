param([string]$SourceDirectory='D:\DLSSNR-Lab\re9-staged-672e0eb',[string]$RestoreBackup='')
$ErrorActionPreference='Stop'
$game='C:\Program Files (x86)\Steam\steamapps\common\RESIDENT EVIL requiem BIOHAZARD requiem'
function Idle {if(Get-Process re9 -ErrorAction SilentlyContinue){throw 'RE9 is running; do not replace loaded files'}}
Idle
if($RestoreBackup){
 $manifest=Get-Content (Join-Path $RestoreBackup 'manifest.json') -Raw|ConvertFrom-Json
 foreach($item in $manifest.files){Idle;$target=Join-Path $game $item.relative;if($item.existed){$from=Join-Path $RestoreBackup $item.relative;if((Get-FileHash $from).Hash -ne $item.before){throw 'Backup hash mismatch'};Copy-Item $from $target -Force;if((Get-FileHash $target).Hash -ne $item.before){throw 'Restore mismatch'}}elseif(Test-Path $target){Remove-Item $target}}
 'RESTORED';exit 0
}
$expectedDll='cc2cdbcaa9e41e39b5db25796822ac4ccad969567d1d2d2c15fb8eed8f1d4861'
$expectedShader='c0f294d8a2b1b11b47e5d14aaea9896406ad71395f15fb4e84427f1ba5a305b0'
$dll=Join-Path $SourceDirectory 're9-present.addon64';$shader=Join-Path $SourceDirectory 'native_codec_decode.hlsl'
if((Get-FileHash $dll).Hash -ne $expectedDll -or (Get-FileHash $shader).Hash -ne $expectedShader){throw 'Candidate hash mismatch'}
if(!(Test-Path "$game\re9.exe") -or !(Test-Path "$game\re9-present.addon64") -or !(Test-Path "$game\DLSS5-AMD\native-game-tiled-assets\native_codec_decode.hlsl")){throw 'Existing RE9 installation not found'}
$plan=@([pscustomobject]@{relative='re9-present.addon64';source=$dll;after=$expectedDll},[pscustomobject]@{relative='DLSS5-AMD\native-game-tiled-assets\native_codec_decode.hlsl';source=$shader;after=$expectedShader})
if(Test-Path "$game\_storage_" -PathType Container){$plan+=[pscustomobject]@{relative='_storage_\re9-present.addon64';source=$dll;after=$expectedDll}}
if(Test-Path "$game\_storage_\DLSS5-AMD\native-game-tiled-assets\native_codec_decode.hlsl"){$plan+=[pscustomobject]@{relative='_storage_\DLSS5-AMD\native-game-tiled-assets\native_codec_decode.hlsl';source=$shader;after=$expectedShader}}
$backup='D:\DLSSNR-Lab\re9-opti\backups\staged-'+(Get-Date -Format 'yyyyMMdd-HHmmss-fff');New-Item -ItemType Directory $backup|Out-Null
$records=@();foreach($item in $plan){$target=Join-Path $game $item.relative;$exists=Test-Path $target;$before=if($exists){(Get-FileHash $target).Hash}else{''};if($exists){$save=Join-Path $backup $item.relative;New-Item -ItemType Directory -Force (Split-Path $save)|Out-Null;Copy-Item $target $save;if((Get-FileHash $save).Hash -ne $before){throw 'Backup mismatch'}};$records+=[pscustomobject]@{relative=$item.relative;existed=$exists;before=$before;after=$item.after}}
$manifest=[pscustomobject]@{game=$game;source_commit='672e0eb';backup=$backup;files=$records}
[IO.File]::WriteAllText((Join-Path $backup 'manifest.json'),($manifest|ConvertTo-Json -Depth 5))
$configs=@('config.ini','DLSS5-AMD\native-game-flags.txt','DLSS5-AMD\re9-present-mode.txt');$configHashes=@{}
foreach($name in $configs){$path=Join-Path $game $name;if(Test-Path $path){$configHashes[$name]=(Get-FileHash $path).Hash}}
foreach($item in $plan){Idle;$target=Join-Path $game $item.relative;Copy-Item $item.source $target -Force;if((Get-FileHash $target).Hash -ne $item.after){throw 'Installed hash mismatch'}}
foreach($name in $configHashes.Keys){if((Get-FileHash (Join-Path $game $name)).Hash -ne $configHashes[$name]){throw 'Configuration changed during deployment'}}
[IO.File]::WriteAllText((Join-Path $SourceDirectory 'installed.json'),($manifest|ConvertTo-Json -Depth 5))
Write-Output "INSTALLED backup=$backup"
$records|ForEach-Object{Write-Output "$($_.relative) $($_.after)"}
