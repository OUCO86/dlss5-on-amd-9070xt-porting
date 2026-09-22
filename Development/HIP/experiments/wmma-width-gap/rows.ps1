$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\wmma-width-gap"
& "$r\check-idle.ps1"
foreach($arch in 'gfx1200','gfx1201'){
 & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$d\rows-$arch.hsaco" "$d\rows.hip" comgr $arch
 if($LASTEXITCODE){throw 'Compile rows failed'}
}
$env:GPU_GAP_CONDITION='1';$folder="$d\fixed-rows";New-Item -ItemType Directory -Force $folder|Out-Null
$p=Start-Process "$r\clock_observe_telemetry.exe" -ArgumentList '600' -PassThru -NoNewWindow -RedirectStandardOutput "$folder\telemetry.log" -RedirectStandardError "$folder\telemetry.err"
Push-Location $folder
try{& "$d\bench-rows.exe" "$d\rows-gfx1201.hsaco" 640 > run.log;if($LASTEXITCODE){throw 'Row test failed'};Get-Content run.log}finally{Pop-Location;if(!$p.HasExited){Stop-Process -Id $p.Id -Force};Remove-Item Env:GPU_GAP_CONDITION -ErrorAction SilentlyContinue}
