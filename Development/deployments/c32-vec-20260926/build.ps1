# c32-wave1 with CW_VEC_INPUT=1 + CW_PREFIX_SPLIT=1 (production recipe) for gfx1200/gfx1201; module sets = vit-proj-n64 production sets with c32-wave1 replaced.
param([string[]]$Architectures=@('gfx1200','gfx1201'))
$ErrorActionPreference='Stop';$d=Split-Path -Parent $MyInvocation.MyCommand.Path;$r='D:\DLSSNR-Lab\hip-backend'
$built=@()
foreach($arch in $Architectures){
 $m="$d\modules-$arch";New-Item -ItemType Directory -Force $m | Out-Null;Copy-Item "$r\vit-proj-n64-production\modules-$arch\*.hsaco" $m
 & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$m\c32-wave1.hsaco" "$d\c32-wave1.hip" comgr $arch
 if($LASTEXITCODE){throw "Compile failed $arch"}
 $built+=@{arch=$arch;module='c32-wave1';source_sha256=(Get-FileHash "$d\c32-wave1.hip").Hash;module_sha256=(Get-FileHash "$m\c32-wave1.hsaco").Hash;count=@(Get-ChildItem $m -Filter *.hsaco).Count}
}
[IO.File]::WriteAllText("$d\build-manifest.json",($built|ConvertTo-Json -Depth 4),(New-Object Text.UTF8Encoding($false)))
$built|ForEach-Object{"{0} {1} {2} modules={3}" -f $_.arch,$_.module,$_.module_sha256,$_.count}
