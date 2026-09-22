$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\wmma-groups-gap"
& "$r\check-idle.ps1"
foreach($arch in 'gfx1200','gfx1201'){
 & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$d\order-$arch.hsaco" "$d\order.hip" comgr $arch
 if($LASTEXITCODE){throw 'Compile order failed'}
}
& "$d\numeric-order.exe" "$d\order-gfx1201.hsaco" > "$d\numeric-order.log"
if($LASTEXITCODE){throw 'Numeric order failed'}
$env:GPU_GAP_CONDITION='1';$folder="$d\order-640";New-Item -ItemType Directory -Force $folder|Out-Null
$p=Start-Process "$r\clock_observe_telemetry.exe" -ArgumentList '600' -PassThru -NoNewWindow -RedirectStandardOutput "$folder\telemetry.log" -RedirectStandardError "$folder\telemetry.err"
Push-Location $folder
try{& "$d\bench-order.exe" "$d\order-gfx1201.hsaco" 640 > run.log;if($LASTEXITCODE){throw 'Order experiment failed'};Get-Content run.log}finally{Pop-Location;if(!$p.HasExited){Stop-Process -Id $p.Id -Force};Remove-Item Env:GPU_GAP_CONDITION -ErrorAction SilentlyContinue}
