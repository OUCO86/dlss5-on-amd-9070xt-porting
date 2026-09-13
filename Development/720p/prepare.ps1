param([string]$Root='D:\DLSSNR-Lab\network-720p',[string]$Base='D:\DLSSNR-Lab\native-game-tiled-assets')
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
$assets=Join-Path $Root 'DLSS5-AMD\native-game-tiled-assets'
New-Item -ItemType Directory -Force $assets,(Join-Path $Root 'DLSS5-AMD\logs') | Out-Null
$canLink=$true
foreach($item in Get-ChildItem $Base -File){
 $dst=Join-Path $assets $item.Name
 if(Test-Path $dst){continue}
 # Only immutable coefficients/maps are hardlinked. Never link shader files that the compiler overwrites.
 if($canLink -and $item.Extension -in @('.f32','.f16','.i32')){try{New-Item -ItemType HardLink -Path $dst -Target $item.FullName | Out-Null}catch{$canLink=$false;Copy-Item $item.FullName $dst}}
 else{Copy-Item $item.FullName $dst}
}
if(!(Test-Path (Join-Path $assets 'noise.f32'))){Copy-Item 'D:\Magpie-DLSS5\Magpie-Experimental-x64\Magpie-Experimental-x64\DLSS5-AMD\native-game-tiled-assets\noise.f32' (Join-Path $assets 'noise.f32')}
Copy-Item (Join-Path $Root 'magpie-flags.txt') (Join-Path $Root 'DLSS5-AMD\native-game-flags.txt') -Force
Write-Output "Prepared isolated assets: $assets"
