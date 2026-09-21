$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$a='D:\DLSSNR-Lab\Magpie-DLSS5-AMD-0.23\DLSS5-AMD';$d="$r\pipeline-gap-results"
function Idle {if(Get-Process LOP-Win64-Shipping,SB-Win64-Shipping,OnimushaWotS,re9,Magpie -ErrorAction SilentlyContinue){throw 'Game running'}}
foreach($height in 900,1080){foreach($graph in 0,1){
 Idle;$dir="$d\$height-g$graph";New-Item -ItemType Directory -Force $dir|Out-Null
 $flags=@(Get-Content "$a\native-game-flags.txt")+@('DLSS5_HIP_MH_FEATURE_BYTE=1','DLSS5_HIP_MH_PROJ_DIAG_FB=1','DLSS5_HIP_MH_BYTE_STREAM=1','DLSS5_HIP_DECODER_BYTE=1','DLSS5_HIP_VIT_BYTE_STREAM=0','DLSS5_HIP_MH_FFN_FRAG256=1',"DLSS5_HIP_GRAPH=$graph",'DLSS5_SHOW_FPS=0','DLSS5_PRE_UPSCALE=0',"DLSS5_NETWORK_HEIGHT=$height",'DLSS5_VIT_ADAPTIVE=0','DLSS5_VIT_REUSE_HOTKEY=0')
 [IO.File]::WriteAllLines("$dir\flags.txt",$flags)
 & "$r\benchmark_pipeline_gap.exe" "$a\native-game-tiled-assets" "$dir\flags.txt" "$r\live-menu-before.f16" "$dir\rgb" 64 0 "$r\post-head-shared-input-modules" 0 1 0 0 > "$dir\run.log" 2> "$dir\stderr.log"
 if($LASTEXITCODE){throw "Probe failed $height $graph"};Idle
 Get-Content "$dir\run.log"|Select-String 'BRIDGE_|BURST|graph_stats'
}
}
