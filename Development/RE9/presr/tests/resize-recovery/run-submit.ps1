$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue'
$busy=Get-Process LOP-Win64-Shipping,SB-Win64-Shipping,OnimushaWotS,re9,Magpie,ronin,Cyberpunk2077 -ErrorAction SilentlyContinue
if($busy){$busy|Select-Object ProcessName,Id;throw 'Game/Magpie running'}
'GPU benchmark guard: idle'
$p=Get-ChildItem D:\ -Directory | ForEach-Object { Get-ChildItem $_.FullName -Directory -Filter 'OptiScaler-REFramework-DLSS5-AMD-0.28' -ErrorAction SilentlyContinue } | Select-Object -First 1
if(!$p){throw 'Package missing'}
$assets=Join-Path $p.FullName 'DLSS5-AMD\native-game-tiled-assets'
$lab='D:\DLSSNR-Lab\re9-presr\resize-candidate'
foreach($glob in '*.hlsl','*.hlsli','*.cso'){Get-ChildItem $assets -Filter $glob | Copy-Item -Destination "$lab\shaders" -Force}
$env:DLSS5_SHADER_DISK_CACHE='0';$env:DLSS5_NETWORK_HEIGHT='auto'
Get-FileHash "$lab\LmxxfNrRuntime.dll" | Format-List
foreach($mode in @(0,1,2,3)){foreach($s in @(@(1280,544),@(960,544))){
 & "$lab\re9-resize-submit.exe" "$lab\LmxxfNrRuntime.dll" "$assets\HIP" $mode $s[0] $s[1]
 if($LASTEXITCODE){throw 'Submit regression failure'}
}}
