$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$a='D:\DLSSNR-Lab\Magpie-DLSS5-AMD-0.23\DLSS5-AMD';$d="$r\full-control-check";New-Item -ItemType Directory -Force $d|Out-Null
if(Get-Process LOP-Win64-Shipping,SB-Win64-Shipping,OnimushaWotS,re9,Magpie -ErrorAction SilentlyContinue){throw 'Game running; skip GPU check'}
$base=@(Get-Content "$a\native-game-flags.txt")+@('DLSS5_NETWORK_HEIGHT=900','DLSS5_PRE_UPSCALE=0','DLSS5_HIP_GRAPH=0','DLSS5_HIP_MH_FEATURE_BYTE=1','DLSS5_HIP_MH_PROJ_DIAG_FB=1','DLSS5_HIP_MH_BYTE_STREAM=1','DLSS5_HIP_DECODER_BYTE=1','DLSS5_HIP_MH_FFN_FRAG256=1','DLSS5_HIP_VIT_BYTE_STREAM=0','DLSS5_VIT_REUSE_HOTKEY=0')
foreach($side in 'reference','forced'){
 $extra=if($side -eq 'reference'){@('DLSS5_SKIP_BLOCKS=','DLSS5_VIT_ADAPTIVE=0')}else{@('DLSS5_SKIP_BLOCKS=42,43,46','DLSS5_VIT_ADAPTIVE=1')}
 [IO.File]::WriteAllLines("$d\$side.txt",($base+$extra))
 $runner=if($side -eq 'reference'){'benchmark_main_reuse.exe'}else{'bench_full_control.exe'}
 & "$r\$runner" "$a\native-game-tiled-assets" "$d\$side.txt" "$r\live-menu-before.f16" "$d\$side" 12 0 "$r\main-reuse-modules" 0 0 0 0 > "$d\$side.log"
 if($LASTEXITCODE){throw 'Replay failed'}
 if(@(Import-Csv "$d\$side.csv"|Where-Object{[int]$_.invalid -ne 0}).Count){throw 'Nonfinite'}
}
if((Get-FileHash "$d\reference.f16").Hash -ne (Get-FileHash "$d\forced.f16").Hash){throw 'Full control differs'}
Write-Output 'PASS forced full build equals configured full-network reference'
Get-FileHash "$d\forced.f16"
