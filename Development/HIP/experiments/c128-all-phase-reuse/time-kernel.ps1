$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\c128-all-phase-reuse-results";$a='D:\DLSSNR-Lab\Magpie-DLSS5-AMD-0.23\DLSS5-AMD'
function Idle {if(Get-Process LOP-Win64-Shipping,SB-Win64-Shipping,OnimushaWotS,re9,Magpie -ErrorAction SilentlyContinue){throw 'Game running'}}
Idle
foreach($slot in 0..3){
 Idle;$candidate=$slot -in 1,2
 if($candidate){Remove-Item Env:DLSS5_C128_M32_DISABLE -ErrorAction SilentlyContinue}else{$env:DLSS5_C128_M32_DISABLE='1'}
 & "$r\pure_c128_all.exe" "$a\native-game-tiled-assets" "$r\c128-all-phase-reuse-modules" "$d\base-900-0\flags.txt" "$r\counter-input.f32" "$r\counter-expected.f32" 2 > "$d\kernel-$slot.log"
 if($LASTEXITCODE){throw 'Kernel repeat output mismatch'}
 Get-Content "$d\kernel-$slot.log" | Select-String 'ROW_REUSE|PURE frame'
}
Remove-Item Env:DLSS5_C128_M32_DISABLE -ErrorAction SilentlyContinue
