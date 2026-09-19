$ErrorActionPreference='Stop'
$g='C:\Program Files (x86)\Steam\steamapps\common\RESIDENT EVIL requiem BIOHAZARD requiem';$r='D:\DLSSNR-Lab\re9-opti';$a="$g\DLSS5-AMD\native-game-tiled-assets";$b="$r\before-info"
if(Get-Process re9,Magpie,SB-Win64-Shipping,LOP-Win64-Shipping -ErrorAction SilentlyContinue){throw 'Game running'}
if(!(Test-Path $b)){New-Item -ItemType Directory $b|Out-Null;Copy-Item "$g\re9-present.addon64","$g\DLSS5-AMD\native-game-flags.txt","$a\native_text_overlay.hlsl" $b}
Copy-Item "$r\native_text_overlay.hlsl" "$a\native_text_overlay.hlsl" -Force
& "$r\install-present.ps1" -Action Update
$f=Get-Content "$g\DLSS5-AMD\native-game-flags.txt" | Where-Object{$_ -notmatch '^DLSS5_(SHOW_FPS|NOTICE)='}
$f+=@('DLSS5_SHOW_FPS=1','DLSS5_NOTICE=2');$f|Set-Content "$g\DLSS5-AMD\native-game-flags.txt" -Encoding ASCII
'1'|Set-Content "$g\DLSS5-AMD\re9-present-mode.txt" -Encoding ASCII
Get-FileHash "$a\native_text_overlay.hlsl"
