$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\wmma-feed-gap"
& "$r\check-idle.ps1"
$env:GPU_GAP_CONDITION='1';$env:GPU_GAP_SWEEP='1';$folder="$d\sweep-640";New-Item -ItemType Directory -Force $folder|Out-Null
$p=Start-Process "$r\clock_observe_telemetry.exe" -ArgumentList '600' -PassThru -NoNewWindow -RedirectStandardOutput "$folder\telemetry.log" -RedirectStandardError "$folder\telemetry.err"
Push-Location $folder
try{& "$d\bench-sweep.exe" "$d\masked-gfx1201.hsaco" 640 > run.log;if($LASTEXITCODE){throw 'Sweep failed'};Get-Content run.log}finally{Pop-Location;if(!$p.HasExited){Stop-Process -Id $p.Id -Force};Remove-Item Env:GPU_GAP_CONDITION,Env:GPU_GAP_SWEEP -ErrorAction SilentlyContinue}
