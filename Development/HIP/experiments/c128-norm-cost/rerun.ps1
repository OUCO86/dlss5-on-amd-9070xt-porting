$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\c128-norm-cost";$a='D:\DLSSNR-Lab\Magpie-DLSS5-AMD-0.23\DLSS5-AMD'
if(Get-Process LOP-Win64-Shipping,SB-Win64-Shipping,OnimushaWotS,re9,Magpie -ErrorAction SilentlyContinue){throw 'Game running'}
& "$d\pure.exe" "$a\native-game-tiled-assets" "$d\modules" "$r\c128-all-phase-reuse-results\base-900-0\flags.txt" "$r\counter-input.f32" "$r\counter-expected.f32" 2 > "$d\run.log"
if($LASTEXITCODE){throw 'Diagnostic failed'}
Get-Content "$d\run.log" | Select-String 'NORM_COST|PURE frame'
