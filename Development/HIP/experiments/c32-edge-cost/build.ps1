$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\c32-edge-cost";$m="$d\modules"
if(Get-Process LOP-Win64-Shipping,SB-Win64-Shipping,OnimushaWotS,re9,Magpie -ErrorAction SilentlyContinue){throw 'Game running'}
New-Item -ItemType Directory -Force $m|Out-Null;Copy-Item "$r\mh-empty-c256-modules\*.hsaco" $m
foreach($arch in 'gfx1200','gfx1201'){
 $file=if($arch -eq 'gfx1201'){"$m\c32_fused_ffn_attention-packed.hsaco"}else{"$d\gfx1200.hsaco"}
 & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' $file "$d\kernel.hip" comgr $arch
 if($LASTEXITCODE){throw 'Compile failed'}
}
