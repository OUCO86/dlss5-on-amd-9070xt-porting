$ErrorActionPreference='Stop';$d='D:\DLSSNR-Lab\hip-backend\c128-row-reuse'
if(Get-Process LOP-Win64-Shipping,SB-Win64-Shipping,OnimushaWotS,re9,Magpie -ErrorAction SilentlyContinue){throw 'Game running'}
foreach($arch in 'gfx1200','gfx1201'){
 & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$d\$arch.hsaco" "$d\kernel.hip" comgr $arch
 if($LASTEXITCODE){throw 'Compile failed'}
}
Set-Location $d
& .\c128-row-bench.exe
if($LASTEXITCODE){throw 'Probe failed'}
if(Get-Process LOP-Win64-Shipping,SB-Win64-Shipping,OnimushaWotS,re9,Magpie -ErrorAction SilentlyContinue){throw 'Game started'}
