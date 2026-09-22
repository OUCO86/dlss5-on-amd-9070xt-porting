$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue'
$busy=Get-Process LOP-Win64-Shipping,SB-Win64-Shipping,OnimushaWotS,re9,Magpie,ronin,Cyberpunk2077 -ErrorAction SilentlyContinue
if($busy){$busy|Select-Object ProcessName,Id;throw 'Game/Magpie running'}
'GPU benchmark guard: idle'
$p=Get-ChildItem D:\ -Directory | ForEach-Object { Get-ChildItem $_.FullName -Directory -Filter 'OptiScaler-REFramework-DLSS5-AMD-0.28' -ErrorAction SilentlyContinue } | Select-Object -First 1
if(!$p){throw 'Package missing'}
$dll=Join-Path $p.FullName 'LmxxfNrRuntime.dll'
if((Get-FileHash $dll).Hash -ne 'F5CF76979D1753CE3E4498F85A45046B984CA8B0E54C80F17A41C45481E7CB68'){throw 'Runtime hash mismatch'}
$env:DLSS5_SHADER_DISK_CACHE='0'
$env:DLSS5_NETWORK_HEIGHT='auto'
foreach($prime in @(0,1)){foreach($s in @(@(1280,544),@(960,544))){
 & D:\DLSSNR-Lab\re9-presr\resize-recovery.exe $dll (Join-Path $p.FullName 'DLSS5-AMD\native-game-tiled-assets\HIP') $prime $s[0] $s[1]
 if($LASTEXITCODE){throw 'Probe process failure'}
}}
