$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\gpu-throughput"
function Idle {if(Get-Process LOP-Win64-Shipping,SB-Win64-Shipping,OnimushaWotS,re9,Magpie -ErrorAction SilentlyContinue){throw 'Game running'}}
Idle
foreach($arch in 'gfx1200','gfx1201'){
 & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$d\$arch.hsaco" "$d\kernel.hip" comgr $arch
 if($LASTEXITCODE){throw 'Compile failed'}
}
Idle
$p=Start-Process "$r\clock_observe_telemetry.exe" -ArgumentList '600' -PassThru -NoNewWindow -RedirectStandardOutput "$d\telemetry.log" -RedirectStandardError "$d\telemetry.err"
Push-Location $d
try{
 & '.\bench.exe' '.\gfx1201.hsaco' > run.log
 if($LASTEXITCODE){throw 'Throughput test failed'}
}finally{Pop-Location;if(!$p.HasExited){Stop-Process -Id $p.Id -Force}}
Idle
Get-Content "$d\run.log"
