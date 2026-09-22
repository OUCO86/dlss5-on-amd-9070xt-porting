param([switch]$Uniform)
$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\wmma-groups-gap"
& "$r\check-idle.ps1"
$prefix=if($Uniform){"uniform-"}else{""};$source=if($Uniform){"$d\uniform.hip"}else{"$d\kernel.hip"}
foreach($arch in 'gfx1200','gfx1201'){
 & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$d\$prefix$arch.hsaco" $source comgr $arch
 if($LASTEXITCODE){throw 'Compile failed'}
}
