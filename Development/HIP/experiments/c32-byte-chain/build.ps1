$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\c32-byte-chain";$m=if($false){"$d\modules-retain"}else{"$d\modules"};$source=if($false){"$d\retain.hip"}else{"$d\kernel.hip"}
& "$r\check-idle.ps1"
New-Item -ItemType Directory -Force $m|Out-Null
Copy-Item "$r\network-fixed-shapes\selected-modules\*.hsaco" $m
foreach($arch in 'gfx1200','gfx1201'){
 $file=if($arch -eq 'gfx1201'){"$m\c32_fused_ffn_attention-packed.hsaco"}else{$(if($false){"$d\retain-gfx1200.hsaco"}else{"$d\gfx1200.hsaco"})}
 & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' $file $source comgr $arch
 if($LASTEXITCODE){throw 'Compile failed'}
}
