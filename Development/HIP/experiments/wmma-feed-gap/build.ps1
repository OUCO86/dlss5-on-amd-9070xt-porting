$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\wmma-feed-gap"
& "$r\check-idle.ps1"
foreach($arch in 'gfx1200','gfx1201'){
 & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$d\masked-$arch.hsaco" "$d\kernel.hip" comgr $arch
 if($LASTEXITCODE){throw 'Compile failed'}
}
