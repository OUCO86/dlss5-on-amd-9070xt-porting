param([ValidateSet('Install','Update','Resume')][string]$Action='Install')
$ErrorActionPreference='Stop'
$g='C:\Program Files (x86)\Steam\steamapps\common\RESIDENT EVIL requiem BIOHAZARD requiem'
$r='D:\DLSSNR-Lab\re9-opti';$b="$r\before-present";$a="$g\DLSS5-AMD\native-game-tiled-assets"
if(Get-Process re9,LOP-Win64-Shipping,SB-Win64-Shipping,Magpie -ErrorAction SilentlyContinue){throw 'Game running'}
if(!(Test-Path "$a\noise.f32")){throw 'Missing noise asset'}
if($Action -eq 'Install'){
 if(Test-Path $b){throw 'Backup exists'}
 New-Item -ItemType Directory $b|Out-Null
 Copy-Item "$g\DLSS5-AMD\native-game-flags.txt" $b
 Copy-Item "$a\native_codec_decode.hlsl" $b
 Copy-Item "$a\HIP" "$b\HIP" -Recurse
 foreach($base in @($g,"$g\_storage_")){
  $o="$base\re9-ffx-observer.addon64"
  if(Test-Path $o){if((Get-FileHash $o).Hash -ne '2bc1ee441c117c349bd30364789f8e23dc7f61d1354e010622fb227060f944e3'){throw 'Unknown observer'};Move-Item $o "$o.off"}
 }
}
if($Action -in 'Install','Resume'){
 $m='D:\DLSSNR-Lab\c256-frag-production-modules'
 foreach($arch in @('gfx1200','gfx1201')){if(Test-Path "$a\HIP\$arch" -PathType Leaf){Remove-Item "$a\HIP\$arch"};New-Item -ItemType Directory -Force "$a\HIP\$arch"|Out-Null;Copy-Item "$m\$arch\*.hsaco" "$a\HIP\$arch\" -Force}
 foreach($line in Get-Content "$m\SHA256SUMS") {if($line -match '^([a-fA-F0-9]{64})\s+\*?(.+)$'){$hash=$matches[1];$path=$matches[2];if((Get-FileHash "$a\HIP\$path").Hash -ne $hash){throw "Module mismatch $path"}}}
 Copy-Item 'D:\DLSSNR-Lab\native_codec_decode.hlsl' "$a\native_codec_decode.hlsl" -Force
 $flags=Get-Content "$g\DLSS5-AMD\native-game-flags.txt"
 $flags=$flags | Where-Object{$_ -notmatch '^DLSS5_(HIP_MH_[A-Z0-9_]+|HIP_VIT_BYTE_STREAM|HIP_DECODER_BYTE|HIP_GRAPH|NETWORK_HEIGHT|CODEC_SRGB|SHOW_FPS|PRE_UPSCALE|PRE_UPSCALE_ASYNC|OUTPUT_SMOOTH|MAKE_RESIDENT_EVERY|RESIDENCY_PRIORITY)='}
 $flags += @('DLSS5_HIP_MH_FEATURE_BYTE=1','DLSS5_HIP_MH_PROJ_DIAG_FB=1','DLSS5_HIP_MH_BYTE_STREAM=1','DLSS5_HIP_VIT_BYTE_STREAM=0','DLSS5_HIP_DECODER_BYTE=1','DLSS5_HIP_MH_FFN_FRAG256=1','DLSS5_HIP_GRAPH=0','DLSS5_NETWORK_HEIGHT=900','DLSS5_CODEC_SRGB=1','DLSS5_SHOW_FPS=0','DLSS5_PRE_UPSCALE=0','DLSS5_PRE_UPSCALE_ASYNC=0')
 $flags|Set-Content "$g\DLSS5-AMD\native-game-flags.txt" -Encoding ASCII
 '0'|Set-Content "$g\DLSS5-AMD\re9-present-mode.txt" -Encoding ASCII
}
foreach($base in @($g,"$g\_storage_")){Copy-Item "$r\re9-present.addon64" "$base\re9-present.addon64" -Force;if((Get-FileHash "$base\re9-present.addon64").Hash -ne (Get-FileHash "$r\re9-present.addon64").Hash){throw 'Addon mismatch'}}
Get-FileHash "$g\re9-present.addon64"
'PRESENT_ADDON_INSTALLED'
