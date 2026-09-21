$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\pipeline-gap-rgp";$tools='C:\Users\lmxxf\Downloads\RadeonDeveloperToolSuite-2026-05-28-1806\RadeonDeveloperToolSuite-2026-05-28-1806';$a='D:\DLSSNR-Lab\Magpie-DLSS5-AMD-0.23\DLSS5-AMD'
if(Get-Process LOP-Win64-Shipping,SB-Win64-Shipping,OnimushaWotS,re9,Magpie -ErrorAction SilentlyContinue){throw 'Game running'}
New-Item -ItemType Directory -Force $d|Out-Null;[IO.File]::WriteAllText("$d\stdin.txt",'')
$arguments=@('-m','profiling','-p','benchmark_main_reuse','-o',"$d\hip.rgp",'--rgp-capture-mode','dispatch','--rgp-auto-capture=dispatch:3000:400','--rgp-render-op-count','400','--rgp-counter-collection','--verbose')
if(Test-Path "$d\hip.rgp"){Move-Item "$d\hip.rgp" "$d\hip-single.rgp" -Force}
$p=Start-Process "$tools\RadeonDeveloperPanelCLI.exe" -ArgumentList $arguments -WorkingDirectory $tools -PassThru -RedirectStandardOutput "$d\cli.log" -RedirectStandardError "$d\cli.err" -RedirectStandardInput "$d\stdin.txt"
try{
 Start-Sleep -Seconds 3
 & "$r\benchmark_main_reuse.exe" "$a\native-game-tiled-assets" "$r\pipeline-gap-results\900-g0\flags.txt" "$r\live-menu-before.f16" "$d\rgb" 2000 0 "$r\post-head-shared-input-modules" 0 1 0 0 > "$d\bench.log" 2> "$d\bench.err"
 if($LASTEXITCODE){throw 'Capture replay failed'}
 Start-Sleep -Seconds 3
}finally{if(!$p.HasExited){Stop-Process -Id $p.Id -Force}}
Get-ChildItem $d -Filter *.rgp|Select-Object Name,Length|ConvertTo-Json
Get-Content "$d\cli.log" -Tail 35
Get-Content "$d\cli.err" -Tail 10
