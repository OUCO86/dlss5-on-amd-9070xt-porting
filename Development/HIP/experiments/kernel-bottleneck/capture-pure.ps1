$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$root="$r\kernel-bottleneck-pure-results";$tools='C:\Users\lmxxf\Downloads\RadeonDeveloperToolSuite-2026-05-28-1806\RadeonDeveloperToolSuite-2026-05-28-1806';$assets='D:\DLSSNR-Lab\Magpie-DLSS5-AMD-0.23\DLSS5-AMD'
function Idle {if(Get-Process LOP-Win64-Shipping,SB-Win64-Shipping,OnimushaWotS,re9,Magpie -ErrorAction SilentlyContinue){throw 'Game running'}}
foreach($case in @(@('c32-post','c32_post_merge_head_half'),@('c128-ffn','mh_ffn_fused_c128_project_mapped_g128_qkv_bytein_fb'),@('c256-ffn','mh_ffn_fused_c256_frag_project_mapped_g128_qkv_bytein_fb'))){
 Idle;$tag=$case[0];$target=$case[1];$d="$root\$tag";New-Item -ItemType Directory -Force $d|Out-Null
 [IO.File]::WriteAllLines("$d\flags.txt",(@(Get-Content "$r\pipeline-gap-results\900-g0\flags.txt")+@("DLSS5_COUNTER_TARGET=$target")))
 [IO.File]::WriteAllText("$d\stdin.txt",'')
 $args=@('-m','profiling','-p','pure_kernel_counter','-o',"$d\trace.rgp",'--rgp-capture-mode','dispatch','--rgp-auto-capture=dispatch:3000:16','--rgp-render-op-count','16','--rgp-counter-collection','--verbose')
 $cli=Start-Process "$tools\RadeonDeveloperPanelCLI.exe" -ArgumentList $args -WorkingDirectory $tools -PassThru -RedirectStandardOutput "$d\cli.log" -RedirectStandardError "$d\cli.err" -RedirectStandardInput "$d\stdin.txt"
 try{Start-Sleep -Seconds 3
  & "$r\pure_kernel_counter.exe" "$assets\native-game-tiled-assets" "$r\post-head-shared-input-modules" "$d\flags.txt" "$r\counter-input.f32" "$r\counter-expected.f32" 2000 > "$d\bench.log" 2> "$d\bench.err"
  if($LASTEXITCODE){throw "Replay failed $tag"};Start-Sleep -Seconds 3
 }finally{if(!$cli.HasExited){Stop-Process -Id $cli.Id -Force}}
 Idle;if(!(Test-Path "$d\trace.rgp")){throw "No trace $tag"}
 if(!(Get-Content "$d\bench.log"|Select-String "COUNTER_TARGET name=$target ")){throw 'Target was not repeated'}
 if(@(Get-Content "$d\bench.log"|Select-String 'PURE frame=.+ bitdiff=0').Count -ne 2){throw 'Pure output mismatch'}
 [pscustomobject]@{case=$tag;trace_bytes=(Get-Item "$d\trace.rgp").Length;target=$target;output_exact=$true}|ConvertTo-Json -Compress
}
