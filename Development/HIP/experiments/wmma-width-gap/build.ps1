param([switch]$Extended,[switch]$Multi)
$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\wmma-width-gap"
& "$r\check-idle.ps1"
$source=if($Multi){"$d\multi.hip"}elseif($Extended){"$d\extended.hip"}else{"$d\kernel.hip"};$prefix=if($Multi){"multi-"}elseif($Extended){"extended-"}else{""}
foreach($arch in 'gfx1200','gfx1201'){
 & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$d\$prefix$arch.hsaco" $source comgr $arch
 if($LASTEXITCODE){throw 'Compile failed'}
}
