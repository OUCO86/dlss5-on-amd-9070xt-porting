# prod6b = prod6 + wave-local QKV normalisation (NOT bit-exact). Built only for the RGB-difference study; not a deployment candidate until the user judges image quality.
$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\fence-prod6"
& "$r\check-idle.ps1"
$m="$r\network-fixed-shapes\prod6b-modules";New-Item -ItemType Directory -Force $m|Out-Null
Copy-Item "$r\network-fixed-shapes\prod6-modules\*.hsaco" $m
& 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$m\multihead-fast-padded-wave-packed.hsaco" "$d\mhfast-6b.generated.hip" comgr gfx1201 | Out-Null
if($LASTEXITCODE){throw "Compile failed 6b"}
"gfx1201 6b "+(Get-FileHash "$m\multihead-fast-padded-wave-packed.hsaco").Hash
