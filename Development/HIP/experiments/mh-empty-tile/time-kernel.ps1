param([ValidateSet('c64','c256')][string]$Variant)
$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\mh-empty-$Variant-results";$a='D:\DLSSNR-Lab\Magpie-DLSS5-AMD-0.23\DLSS5-AMD'
function Idle {if(Get-Process LOP-Win64-Shipping,SB-Win64-Shipping,OnimushaWotS,re9,Magpie -ErrorAction SilentlyContinue){throw 'Game running'}}
Idle;New-Item -ItemType Directory -Force $d|Out-Null
$targets=@($Variant)
foreach($target in $targets){
 $env:DLSS5_EMPTY_TARGET=if($target -eq 'c64'){'mh_ffn_fused_c64_project_mapped_g128_qkv_bytein_fb'}else{'mh_ffn_fused_c256_frag_project_mapped_g128_qkv_bytein_fb'}
 foreach($slot in 0..3){
  Idle;$m=if($slot -in 1,2){"$r\mh-empty-$Variant-modules"}else{"$r\c128-empty-vertical-modules"}
  & "$r\pure_mh_empty.exe" "$a\native-game-tiled-assets" $m "$r\c128-all-phase-reuse-results\base-900-0\flags.txt" "$r\counter-input.f32" "$r\counter-expected.f32" 2 > "$d\kernel-$target-$slot.log"
  if($LASTEXITCODE){throw 'Raw output changed'}
  Get-Content "$d\kernel-$target-$slot.log" | Select-String 'EMPTY_TILE|PURE frame'
 }
}
Remove-Item Env:DLSS5_EMPTY_TARGET -ErrorAction SilentlyContinue
