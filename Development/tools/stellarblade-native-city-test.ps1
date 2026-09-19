param([ValidateSet('Native','Restore','Status')][string]$Action='Status')
$ErrorActionPreference='Stop'
$game='C:\Program Files (x86)\Steam\steamapps\common\StellarBlade\SB\Binaries\Win64'
$original='D:\DLSSNR-Lab\stellarblade-before-optiscaler'
$backup='D:\DLSSNR-Lab\pre-upscale\before-native-city-test'
function Closed {if(Get-Process SB-Win64-Shipping -ErrorAction SilentlyContinue){throw 'Exit Stellar Blade first.'}}
function RestoreFiles($records){
 Closed
 foreach($r in $records){if((Get-FileHash "$backup\files\$($r.name)").Hash -ne $r.sha256){throw 'Backup hash mismatch'}}
 foreach($r in $records){Copy-Item "$backup\files\$($r.name)" "$game\$($r.name)" -Force;if((Get-FileHash "$game\$($r.name)").Hash -ne $r.sha256){throw 'Restored hash mismatch'}}
}
if($Action -eq 'Native'){
 Closed
 if(Test-Path $backup){throw 'Native comparison backup already exists; inspect it first'}
 if(Test-Path "$game\d3d12.dll"){throw 'Unexpected local d3d12.dll; inspect loader before native comparison'}
 $old=Get-Content "$original\manifest.json" -Raw|ConvertFrom-Json
 if($old.saved -notcontains 'amd_fidelityfx_dx12.dll'){throw 'Original FSR not in pre-OptiScaler backup'}
 $originalHash=(Get-FileHash "$original\amd_fidelityfx_dx12.dll").Hash
 $names=@($old.install|Where-Object{$_ -match '\.(dll|addon64)$' -and (Test-Path "$game\$_")})
 if($names -notcontains 'dxgi.dll' -or $names -notcontains 'dlss5-amd.addon64'){throw 'Expected current plugin installation missing'}
 New-Item -ItemType Directory "$backup\files" -Force|Out-Null
 $records=@(foreach($name in $names){
  $hash=(Get-FileHash "$game\$name").Hash;Copy-Item "$game\$name" "$backup\files\$name"
  if((Get-FileHash "$backup\files\$name").Hash -ne $hash){throw 'Backup verification failed'}
  [pscustomobject]@{name=$name;sha256=$hash}
 })
 [pscustomobject]@{files=$records;originalFsrSha=$originalHash}|ConvertTo-Json -Depth 4|Set-Content "$backup\manifest.json"
 $settings=Join-Path $env:LOCALAPPDATA 'SB\Saved\Config\WindowsNoEditor\GameUserSettings.ini'
 $settingsHash=(Get-FileHash $settings).Hash
 Copy-Item $settings "$backup\GameUserSettings.ini.snapshot"
 Copy-Item "$game\OptiScaler.ini" "$backup\OptiScaler.ini.snapshot"
 Copy-Item "$game\DLSS5-AMD\native-game-flags.txt" "$backup\native-game-flags.txt.snapshot"
 try{
  Closed
  foreach($r in $records){Remove-Item -LiteralPath "$game\$($r.name)"}
  Copy-Item "$original\amd_fidelityfx_dx12.dll" "$game\amd_fidelityfx_dx12.dll"
  if((Get-FileHash "$game\amd_fidelityfx_dx12.dll").Hash -ne $originalHash){throw 'Original FSR verification failed'}
  foreach($r in $records){if($r.name -ne 'amd_fidelityfx_dx12.dll' -and (Test-Path "$game\$($r.name)")){throw 'Plugin binary still present'}}
  if((Get-FileHash $settings).Hash -ne $settingsHash){throw 'Game settings changed during preparation'}
  'native'|Set-Content "$backup\state.txt"
  "NATIVE_READY disabled_binaries=$($records.Count-1) original_fsr_sha=$originalHash settings_unchanged=1 backup=$backup"
 }catch{RestoreFiles $records;throw}
}elseif($Action -eq 'Restore'){
 $m=Get-Content "$backup\manifest.json" -Raw|ConvertFrom-Json
 RestoreFiles @($m.files)
 'restored'|Set-Content "$backup\state.txt"
 'PLUGIN_CHAIN_RESTORED; current game graphics settings preserved'
}else{
 Get-Process SB-Win64-Shipping -ErrorAction SilentlyContinue|Select-Object Id,ProcessName
 if(Test-Path "$backup\state.txt"){Get-Content "$backup\state.txt"}
 foreach($n in @('dxgi.dll','d3d12.dll','ReShade64.dll','dlss5-amd.addon64','amd_fidelityfx_dx12.dll')){
  if(Test-Path "$game\$n"){Get-FileHash "$game\$n"|Select-Object Path,Hash}
 }
}
