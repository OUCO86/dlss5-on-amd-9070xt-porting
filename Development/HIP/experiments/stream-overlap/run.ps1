$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\stream-overlap"
& "$r\check-idle.ps1"
& 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$d\spin.hsaco" "$d\spin.hip" comgr gfx1201 | Out-Null
if($LASTEXITCODE){throw 'spin compile failed'}
'== default =='
& "$d\check_stream_overlap.exe" "$d\spin.hsaco"
if($LASTEXITCODE){throw "probe failed $LASTEXITCODE"}
'== GPU_MAX_HW_QUEUES=4 =='
$env:GPU_MAX_HW_QUEUES='4'
& "$d\check_stream_overlap.exe" "$d\spin.hsaco"
Remove-Item Env:GPU_MAX_HW_QUEUES
