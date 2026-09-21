$ErrorActionPreference='Stop'
$r='D:\DLSSNR-Lab\hip-backend'
if(Get-Process LOP-Win64-Shipping,SB-Win64-Shipping,OnimushaWotS,re9,Magpie -ErrorAction SilentlyContinue){throw 'Game running'}
$d="$r\c128-compact-reuse-modules"
New-Item -ItemType Directory -Force $d|Out-Null
Copy-Item "$r\post-head-shared-input-modules\*" $d -Recurse -Force
foreach($arch in 'gfx1200','gfx1201'){
 $file=if($arch -eq 'gfx1201'){"$d\multihead-fast-padded-wave-packed.hsaco"}else{"$r\c128-compact-reuse-gfx1200.hsaco"}
 & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' $file "$r\c128-compact-reuse.hip" comgr $arch
 if($LASTEXITCODE){throw 'Compile failed'}
}
