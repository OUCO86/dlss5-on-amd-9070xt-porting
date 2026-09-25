$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\stream-overlap"
& "$r\check-idle.ps1"
& 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$d\pdl.hsaco" "$d\pdl.hip" comgr gfx1201 | Out-Null
if($LASTEXITCODE){throw 'pdl compile failed'}
& "$d\check_pdl.exe" "$d\pdl.hsaco"
if($LASTEXITCODE){throw "probe failed $LASTEXITCODE"}
