$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$lab='D:\DLSSNR-Lab'
$flags='DLSS5_HIP_MH_FEATURE_BYTE=1;DLSS5_HIP_MH_PROJ_DIAG_FB=1;DLSS5_HIP_MH_BYTE_STREAM=1;DLSS5_HIP_DECODER_BYTE=1;DLSS5_HIP_VIT_BYTE_STREAM=0;DLSS5_HIP_MH_FFN_FRAG256=1;DLSS5_HIP_GRAPH=0'
foreach($h in 900,1080){foreach($v in 'base','pair'){
 if(Get-Process re9,SB-Win64-Shipping,LOP-Win64-Shipping,Magpie -ErrorAction SilentlyContinue){throw 'Game/Magpie running'}
 $m=if($v -eq 'base'){"$lab\c256-frag-production-modules\gfx1201"}else{"$r\vit-kv-pair-modules"}
 & "$r\profile-1080.ps1" -Families 'none,vitattn,none' -Frames 160 -WarmupFrames 32 -Tag "vitpair-marginal-$h-$v" -ExtraFlag "$flags;DLSS5_NETWORK_HEIGHT=$h" -Modules $m -Runner benchmark_c256frag_production.exe -TimingOnly
}}
