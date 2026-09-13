param(
 [ValidateSet('Deploy','Restore')][string]$Action='Deploy',
 [switch]$StopMagpie,
 [ValidateSet(720,900,1080)][int]$NetworkHeight=720,
 [string]$Root='D:\DLSSNR-Lab\network-720p',
 [string]$SourceAssets='',
 [string]$ExpectedAddon='A9E27526AAA22B5102ED133A4D3CA1D8FD8EAE40C8EBE1D6F74951BBC079D3E9'
)
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
$target='D:\Magpie-DLSS5\Magpie-Experimental-x64\Magpie-Experimental-x64'
if(!$SourceAssets){$SourceAssets=Join-Path $Root 'DLSS5-AMD\native-game-tiled-assets'}
$targetAssets=Join-Path $target 'DLSS5-AMD\native-game-tiled-assets'
$backup=Join-Path $Root ('before-magpie-'+$NetworkHeight+'p')
$flags=Join-Path $target 'DLSS5-AMD\native-game-flags.txt'
$expected=$ExpectedAddon
$utf8=New-Object System.Text.UTF8Encoding($false)
$running=@(Get-Process *Magpie* -ErrorAction SilentlyContinue | Where-Object {$_.Path -eq (Join-Path $target 'Magpie.exe')})
if($running.Count){
 if(!$StopMagpie){throw 'Exit Magpie before deploying or restoring.'}
 $running | Stop-Process -Force
 foreach($p in $running){$p.WaitForExit(5000) | Out-Null}
}
if(Get-Process *Magpie* -ErrorAction SilentlyContinue | Where-Object {$_.Path -eq (Join-Path $target 'Magpie.exe')}){throw 'Magpie is still running.'}
function Restore-Backup {
 if(!(Test-Path (Join-Path $backup 'complete'))){throw 'No complete deployment backup.'}
 $changes=Get-Content (Join-Path $backup 'changes.json') -Raw | ConvertFrom-Json
 foreach($c in $changes){
  $dst=Join-Path $target $c.relative
  if($c.existed){Copy-Item (Join-Path $backup $c.relative) $dst -Force}
  elseif(Test-Path $dst){Remove-Item $dst -Force}
 }
 Copy-Item (Join-Path $backup 'native-game-flags.txt') $flags -Force
}
if($Action -eq 'Restore'){Restore-Backup;'Restored previous Magpie DLL, shaders, manifest and flags.';exit 0}
if(Test-Path $backup){throw 'Backup already exists; inspect before redeploying.'}
if((Get-FileHash (Join-Path $root 'dlss5-amd.addon64')).Hash -ne $expected){throw 'Candidate addon hash differs.'}
foreach($name in @('native_wave_vit_qkv_fused_m1.cso','native_wave_vit_expand_packed.cso','native_wave_vit_attention_fp8.cso','native_game_rgb_input.hlsl','native_rgb_texture.hlsl','native_temporal_feed.hlsl','native_vit_linear.hlsl')){
 if(!(Test-Path (Join-Path $sourceAssets $name))){throw "Candidate shader missing: $name"}
}
$items=@(@{source=(Join-Path $root 'dlss5-amd.addon64');relative='dlss5-amd.addon64'})
foreach($f in Get-ChildItem $sourceAssets -File | Where-Object {$_.Extension -in @('.cso','.hlsl','.hlsli')}){
 $dst=Join-Path $targetAssets $f.Name
 if(!(Test-Path $dst) -or (Get-FileHash $dst).Hash -ne (Get-FileHash $f.FullName).Hash){
  $items+=@{source=$f.FullName;relative=('DLSS5-AMD\native-game-tiled-assets\'+$f.Name)}
 }
}
# The manifest is generated after deployment, so back it up separately too.
$manifestRelative='DLSS5-AMD\native-game-tiled-assets\shader-manifest.json'
$backupItems=@($items)+@(@{source='';relative=$manifestRelative})
New-Item -ItemType Directory $backup | Out-Null
$changes=@()
foreach($item in $backupItems){
 $dst=Join-Path $target $item.relative;$existed=Test-Path $dst
 $changes+=@{relative=$item.relative;existed=$existed}
 if($existed){$save=Join-Path $backup $item.relative;New-Item -ItemType Directory -Force (Split-Path $save -Parent) | Out-Null;Copy-Item $dst $save -Force}
}
Copy-Item $flags (Join-Path $backup 'native-game-flags.txt')
[IO.File]::WriteAllText((Join-Path $backup 'changes.json'),($changes | ConvertTo-Json -Depth 5),$utf8)
[IO.File]::WriteAllText((Join-Path $backup 'complete'),'1',$utf8)
try{
 foreach($item in $items){Copy-Item $item.source (Join-Path $target $item.relative) -Force}
 $newFlags=@(Get-Content $flags | Where-Object {$_ -notmatch '^DLSS5_NETWORK_(720P|HEIGHT)='})+@('DLSS5_NETWORK_HEIGHT='+$NetworkHeight)
 [IO.File]::WriteAllLines($flags,$newFlags,$utf8)
 $manifest=@(Get-ChildItem $targetAssets -File | Where-Object {$_.Extension -in @('.hlsl','.hlsli')} | ForEach-Object {@{name=$_.Name;sha256=(Get-FileHash $_.FullName).Hash.ToLowerInvariant()}})
 [IO.File]::WriteAllText((Join-Path $target $manifestRelative),($manifest | ConvertTo-Json -Depth 4),$utf8)
 foreach($item in $items){if((Get-FileHash $item.source).Hash -ne (Get-FileHash (Join-Path $target $item.relative)).Hash){throw "Installed hash mismatch: $($item.relative)"}}
 if((Get-Content $flags) -notcontains ('DLSS5_NETWORK_HEIGHT='+$NetworkHeight)){throw 'Network height flag missing.'}
 Write-Output ('COPIED_FILES='+$items.Count)
 Write-Output ('ADDON='+(Get-FileHash (Join-Path $target 'dlss5-amd.addon64')).Hash)
 Write-Output ('BACKUP='+$backup)
 Write-Output ('NETWORK_HEIGHT='+$NetworkHeight)
}catch{Restore-Backup;throw}
