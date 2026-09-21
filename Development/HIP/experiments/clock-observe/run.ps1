$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\clock-observe-results";$a='D:\DLSSNR-Lab\Magpie-DLSS5-AMD-0.23\DLSS5-AMD'
function Idle {if(Get-Process LOP-Win64-Shipping,SB-Win64-Shipping,OnimushaWotS,re9,Magpie -ErrorAction SilentlyContinue){throw 'Game running'}}
Idle;New-Item -ItemType Directory -Force $d|Out-Null
foreach($height in 900,1080){
 Idle;$folder="$d\$height";New-Item -ItemType Directory -Force $folder|Out-Null
 $flags=@(Get-Content "$r\pipeline-gap-results\$height-g0\flags.txt")
 [IO.File]::WriteAllLines("$folder\flags.txt",$flags)
 $p=Start-Process "$r\clock_observe_telemetry.exe" -ArgumentList '200' -PassThru -NoNewWindow -RedirectStandardOutput "$folder\telemetry.log" -RedirectStandardError "$folder\telemetry.err"
 try{
  & "$r\benchmark_clock_observe.exe" "$a\native-game-tiled-assets" "$folder\flags.txt" "$r\live-menu-before.f16" "$folder\rgb" 1000 0 "$r\post-head-shared-input-modules" 0 1 0 0 > "$folder\run.log"
  if($LASTEXITCODE){throw 'Benchmark failed'}
 }finally{if(!$p.HasExited){Stop-Process -Id $p.Id -Force}}
 Idle;Get-FileHash "$folder\rgb.f16"
}
