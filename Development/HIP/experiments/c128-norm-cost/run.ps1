$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\c128-norm-cost";$a='D:\DLSSNR-Lab\Magpie-DLSS5-AMD-0.23\DLSS5-AMD'
function Idle {if(Get-Process LOP-Win64-Shipping,SB-Win64-Shipping,OnimushaWotS,re9,Magpie -ErrorAction SilentlyContinue){throw 'Game running'}}
Idle
New-Item -ItemType Directory -Force $d|Out-Null
foreach($arch in 'gfx1200','gfx1201'){
 & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$d\$arch.hsaco" "$d\kernel.hip" comgr $arch
 if($LASTEXITCODE){throw 'Compile failed'}
}
$m="$d\modules";New-Item -ItemType Directory -Force $m|Out-Null
Copy-Item "$r\post-head-shared-input-modules\*" $m -Recurse -Force
Copy-Item "$d\gfx1201.hsaco" "$m\multihead-fast-padded-wave-packed.hsaco" -Force
Idle
& "$d\pure.exe" "$a\native-game-tiled-assets" $m "$r\c128-all-phase-reuse-results\base-900-0\flags.txt" "$r\counter-input.f32" "$r\counter-expected.f32" 2 > "$d\run.log"
if($LASTEXITCODE){throw 'Diagnostic output changed'}
Get-Content "$d\run.log" | Select-String 'NORM_COST|PURE frame'
