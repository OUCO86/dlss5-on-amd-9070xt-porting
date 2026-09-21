param([ValidateSet('c64','c256')][string]$Variant)
$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\mh-empty-$Variant-modules"
if(Get-Process LOP-Win64-Shipping,SB-Win64-Shipping,OnimushaWotS,re9,Magpie -ErrorAction SilentlyContinue){throw 'Game running'}
New-Item -ItemType Directory -Force $d|Out-Null
Copy-Item "$r\c128-empty-vertical-modules\*" $d -Recurse -Force
foreach($arch in 'gfx1200','gfx1201'){
 $file=if($arch -eq 'gfx1201'){"$d\multihead-fast-padded-wave-packed.hsaco"}else{"$r\mh-empty-$Variant-gfx1200.hsaco"}
 & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' $file "$r\mh-empty-$Variant.hip" comgr $arch
 if($LASTEXITCODE){throw 'Compile failed'}
}
