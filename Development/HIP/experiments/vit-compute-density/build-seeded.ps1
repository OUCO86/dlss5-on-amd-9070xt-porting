$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\vit-compute-density";$m="$d\modules-seeded"
if(Get-Process LOP-Win64-Shipping,SB-Win64-Shipping,OnimushaWotS,re9,Magpie -ErrorAction SilentlyContinue){throw 'Game running'}
New-Item -ItemType Directory -Force $m|Out-Null;Copy-Item "$r\network-fixed-shapes\selected-modules\*.hsaco" $m
foreach($arch in 'gfx1200','gfx1201'){
 $file=if($arch -eq 'gfx1201'){"$m\deep_fast-packed.hsaco"}else{"$d\seeded-gfx1200.hsaco"}
 & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' $file "$d\seeded.hip" comgr $arch
 if($LASTEXITCODE){throw 'Compile failed'}
}
