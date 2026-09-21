$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\gpu-throughput"
function Idle {if(Get-Process LOP-Win64-Shipping,SB-Win64-Shipping,OnimushaWotS,re9,Magpie -ErrorAction SilentlyContinue){throw 'Game running'}}
$env:GPU_THROUGHPUT_BATCH_MS='300';$env:GPU_THROUGHPUT_SAMPLES='9'
foreach($kind in 'fp8','fp16','fp32d'){
 Idle;$folder="$d\repeat-$kind";New-Item -ItemType Directory -Force $folder|Out-Null
 $acc=if($kind -eq 'fp32d'){16}else{8}
 $p=Start-Process "$r\clock_observe_telemetry.exe" -ArgumentList '600' -PassThru -NoNewWindow -RedirectStandardOutput "$folder\telemetry.log" -RedirectStandardError "$folder\telemetry.err"
 Push-Location $folder
 try{& "$d\bench.exe" "$d\gfx1201.hsaco" $kind $acc 256 > run.log;if($LASTEXITCODE){throw 'Repeat failed'}}finally{Pop-Location;if(!$p.HasExited){Stop-Process -Id $p.Id -Force}}
 Get-Content "$folder\run.log"
}
Remove-Item Env:GPU_THROUGHPUT_BATCH_MS,Env:GPU_THROUGHPUT_SAMPLES -ErrorAction SilentlyContinue
