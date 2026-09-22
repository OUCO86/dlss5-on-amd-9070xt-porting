$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\vit-eight-accumulators";$m="$d\modules-u2"
& "$r\check-idle.ps1"
New-Item -ItemType Directory -Force $m|Out-Null
Copy-Item "$r\network-fixed-shapes\selected-modules\*.hsaco" $m
foreach($arch in 'gfx1200','gfx1201'){
 $file=if($arch -eq 'gfx1201'){"$m\deep_fast-packed.hsaco"}else{"$d\u2-gfx1200.hsaco"}
 & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' $file "$d\u2.hip" comgr $arch
 if($LASTEXITCODE){throw 'Compile failed'}
}
