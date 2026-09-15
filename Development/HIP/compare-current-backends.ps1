$ErrorActionPreference='Stop'
$r='D:\DLSSNR-Lab\hip-backend'
foreach($i in 0..3){
 if(Get-Process SB-Win64-Shipping -ErrorAction SilentlyContinue){throw 'Game running'}
 $exe=if($i -in @(0,3)){'benchmark_hlsl_current.exe'}else{'benchmark_identity.exe'}
 & "$r\validate-hdr.ps1" -Runner $exe -Modules c32-input-dword-release-modules -Name "backend-current-$i" -Flags rebind-async-flags.txt
 if(Get-Process SB-Win64-Shipping -ErrorAction SilentlyContinue){throw 'Game started'}
}
