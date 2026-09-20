param([switch]$BuildOnly)
$ErrorActionPreference='Stop';$lab='D:\DLSSNR-Lab';$r="$lab\hip-backend";$src="$lab\vit-kv-pair-src";$build="$lab\vit-kv-pair-build"
function Idle {if(Get-Process re9,SB-Win64-Shipping,LOP-Win64-Shipping,Magpie -ErrorAction SilentlyContinue){throw 'Game/Magpie running; no GPU measurements'}}
Idle
New-Item -ItemType Directory -Force $src|Out-Null;Copy-Item "$r\vit-kv-pair.hip" "$src\deep_fast.hip" -Force
& "$r\build-vIT-experiment.ps1" -SourceDir $src -OutputDir $build -Compiler "$lab\dual-arch-src\rtc_compile.exe" -Only deep_fast-packed
if($BuildOnly){exit}
$base="$lab\c256-frag-production-modules\gfx1201";$candidate="$r\vit-kv-pair-modules"
New-Item -ItemType Directory -Force $candidate|Out-Null;Copy-Item "$base\*.hsaco" $candidate -Force;Copy-Item "$build\gfx1201\deep_fast-packed.hsaco" $candidate -Force
$flags='DLSS5_HIP_MH_FEATURE_BYTE=1;DLSS5_HIP_MH_PROJ_DIAG_FB=1;DLSS5_HIP_MH_BYTE_STREAM=1;DLSS5_HIP_DECODER_BYTE=1;DLSS5_HIP_VIT_BYTE_STREAM=0;DLSS5_HIP_MH_FFN_FRAG256=1;DLSS5_HIP_GRAPH=0'
foreach($height in 900,1080){foreach($i in 0..3){Idle;$m=if($i -in 1,2){$candidate}else{$base};$tag="vitpair-$height-$i"
 & "$r\profile-1080.ps1" -Frames 160 -WarmupFrames 32 -Tag $tag -ExtraFlag "$flags;DLSS5_NETWORK_HEIGHT=$height" -Modules $m -Runner benchmark_c256frag_production.exe -TimingOnly
 Idle
}}
