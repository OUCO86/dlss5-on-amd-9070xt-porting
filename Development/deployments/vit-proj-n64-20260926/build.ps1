# Build the opt-in ViT projection 64-column module for gfx1200/gfx1201 next to the production module sets
# (wave-owned production + C512 32-token payload).
param([string[]]$Architectures=@('gfx1200','gfx1201'))
$ErrorActionPreference='Stop';$d=Split-Path -Parent $MyInvocation.MyCommand.Path;$r='D:\DLSSNR-Lab\hip-backend'
$built=@()
foreach($arch in $Architectures){
 $m="$d\modules-$arch";New-Item -ItemType Directory -Force $m | Out-Null;Copy-Item "$r\wave-owned-production\modules-$arch\*.hsaco" $m;Copy-Item "D:\DLSSNR-Lab\c512-m32-20260926\payload\$arch\*.hsaco" $m
 & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$m\vit-wide-deep.hsaco" "$d\vit-wide-deep.hip" comgr $arch
 if($LASTEXITCODE){throw "Compile failed $arch"}
 $built+=@{arch=$arch;module='vit-wide-deep';source_sha256=(Get-FileHash "$d\vit-wide-deep.hip").Hash;module_sha256=(Get-FileHash "$m\vit-wide-deep.hsaco").Hash}
}
[IO.File]::WriteAllText("$d\build-manifest.json",($built|ConvertTo-Json -Depth 4),(New-Object Text.UTF8Encoding($false)))
$built|ForEach-Object{"{0} {1} {2}" -f $_.arch,$_.module,$_.module_sha256}
