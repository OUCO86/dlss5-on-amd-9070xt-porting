param([ValidateSet('Deploy','Restore')][string]$Action='Deploy')
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
$lab='D:\DLSSNR-Lab'
$game='C:\Program Files (x86)\Steam\steamapps\common\StellarBlade\SB\Binaries\Win64'
$root=Join-Path $lab 'network-900p'
$sourceAssets=Join-Path $lab 'network-720p\DLSS5-AMD\native-game-tiled-assets'
$assets=Join-Path $lab 'native-game-tiled-assets'
$backup=Join-Path $root 'before-stellarblade-900p'
$expected='72F87A97BFB3AD5D0EFD3FF11DA56B8FBFB778478BE2DF908E30E43CDCE15FD2'
$utf8=New-Object System.Text.UTF8Encoding($false)
function Assert-GameClosed {if(Get-Process SB-Win64-Shipping -ErrorAction SilentlyContinue){throw 'Stellar Blade is running; close it before deploying/restoring.'}}
Assert-GameClosed
if(Test-Path (Join-Path $game 'DLSS5-AMD\native-game-flags.txt')){throw 'Game-local DLSS5-AMD shadows the lab root; inspect it before deployment.'}
function Restore-Backup {
 if(!(Test-Path (Join-Path $backup 'complete'))){throw 'No complete backup.'}
 foreach($item in (Get-Content (Join-Path $backup 'changes.json') -Raw | ConvertFrom-Json)){
  if($item.existed){Copy-Item (Join-Path $backup $item.saved) $item.target -Force}
  elseif(Test-Path $item.target){Remove-Item $item.target -Force}
 }
}
if($Action -eq 'Restore'){Restore-Backup;'Restored previous Stellar Blade add-on, shaders and flags.';exit 0}
if(Test-Path $backup){throw 'Backup already exists; inspect before redeploying.'}
$dll=Join-Path $root 'dlss5-amd.addon64'
if((Get-FileHash $dll).Hash -ne $expected){throw 'Candidate DLL hash differs.'}
foreach($name in @('d3d12.dll','amd_fidelityfx_dx12.dll','DLSS5-D3D12-721\D3D12Core.dll')){if(!(Test-Path (Join-Path $game $name))){throw "Game dependency missing: $name"}}
if(!(Test-Path (Join-Path $assets 'noise.f32')) -and !(Test-Path (Join-Path $lab 'matrix-probe\native-runtime-rgb512\functions.f32'))){throw 'Noise asset missing.'}
$items=@(@{source=$dll;target=(Join-Path $game 'native-submission-order.addon64');saved='native-submission-order.addon64'})
foreach($f in Get-ChildItem $sourceAssets -File | Where-Object {$_.Extension -in @('.cso','.hlsl','.hlsli')}){
 $dst=Join-Path $assets $f.Name
 if(!(Test-Path $dst) -or (Get-FileHash $dst).Hash -ne (Get-FileHash $f.FullName).Hash){$items+=@{source=$f.FullName;target=$dst;saved=('shaders\'+$f.Name)}}
}
$flags=Join-Path $lab 'native-game-flags.txt'
$manifest=Join-Path $assets 'shader-manifest.json'
$extra=@(@{source='';target=$flags;saved='native-game-flags.txt'},@{source='';target=$manifest;saved='shader-manifest.json'})
foreach($name in @('enable-game-sdk721.txt','continuous-every-frame.txt','temporal-history.txt')){$extra+=@{source='';target=(Join-Path $lab $name);saved=$name}}
New-Item -ItemType Directory $backup | Out-Null
$changes=@()
foreach($item in (@($items)+@($extra))){
 $exists=Test-Path $item.target;$changes+=@{target=$item.target;saved=$item.saved;existed=$exists}
 if($exists){$save=Join-Path $backup $item.saved;New-Item -ItemType Directory -Force (Split-Path $save -Parent) | Out-Null;Copy-Item $item.target $save -Force}
}
[IO.File]::WriteAllText((Join-Path $backup 'changes.json'),($changes | ConvertTo-Json -Depth 4),$utf8)
[IO.File]::WriteAllText((Join-Path $backup 'complete'),'1',$utf8)
Assert-GameClosed
try{
 foreach($item in $items){Copy-Item $item.source $item.target -Force}
 # Preserve existing game tuning; replace only integration options and remove old diagnostics.
 $new=@(Get-Content $flags | Where-Object {$_ -notmatch '^DLSS5_(NETWORK_(720P|HEIGHT)|FIT_INPUT|CODEC_SRGB|SHOW_FPS|DEBUG_DUMPS|BLACK_PROBE|GAME_PROBE|DEBUG_TINT|RESERVE_VRAM_MB)='})
 $new+=@('DLSS5_NETWORK_HEIGHT=900','DLSS5_FIT_INPUT=1','DLSS5_CODEC_SRGB=0','DLSS5_SHOW_FPS=1')
 [IO.File]::WriteAllLines($flags,$new,$utf8)
 foreach($name in @('enable-game-sdk721.txt','continuous-every-frame.txt','temporal-history.txt')){[IO.File]::WriteAllText((Join-Path $lab $name),"1`n",$utf8)}
 $m=@(Get-ChildItem $assets -File | Where-Object {$_.Extension -in @('.hlsl','.hlsli')} | ForEach-Object {@{name=$_.Name;sha256=(Get-FileHash $_.FullName).Hash.ToLowerInvariant()}})
 [IO.File]::WriteAllText($manifest,($m | ConvertTo-Json -Depth 4),$utf8)
 foreach($item in $items){if((Get-FileHash $item.source).Hash -ne (Get-FileHash $item.target).Hash){throw "Installed hash mismatch: $($item.target)"}}
 $actual=Get-Content $flags
 foreach($f in @('DLSS5_NETWORK_HEIGHT=900','DLSS5_FIT_INPUT=1','DLSS5_CODEC_SRGB=0','DLSS5_SHOW_FPS=1')){if($actual -notcontains $f){throw "Missing flag $f"}}
 if($actual -match '^DLSS5_(DEBUG_DUMPS|BLACK_PROBE|GAME_PROBE)=1$'){throw 'Diagnostics still enabled.'}
 'COPIED_FILES='+$items.Count
 'ADDON='+(Get-FileHash (Join-Path $game 'native-submission-order.addon64')).Hash
 'BACKUP='+$backup
 'GAME_MODE=900p inference, linear color codec, native engine motion, temporal on, FPS on'
}catch{Restore-Backup;throw}
