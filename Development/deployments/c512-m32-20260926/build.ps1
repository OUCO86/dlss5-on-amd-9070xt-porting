# Build the two opt-in C512 32-token modules for gfx1200/gfx1201 next to the wave-owned production module sets.
param([string[]]$Architectures=@('gfx1200','gfx1201'))
$ErrorActionPreference='Stop';$d=Split-Path -Parent $MyInvocation.MyCommand.Path;$r='D:\DLSSNR-Lab\hip-backend'
$built=@()
foreach($arch in $Architectures){
 $m="$d\modules-$arch";New-Item -ItemType Directory -Force $m | Out-Null;Copy-Item "$r\wave-owned-production\modules-$arch\*.hsaco" $m
 foreach($name in 'c512-m32-mh','c512-m32-deep'){
  & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$m\$name.hsaco" "$d\$name.hip" comgr $arch
  if($LASTEXITCODE){throw "Compile failed $arch $name"}
  $built+=@{arch=$arch;module=$name;source_sha256=(Get-FileHash "$d\$name.hip").Hash;module_sha256=(Get-FileHash "$m\$name.hsaco").Hash}
 }
}
[IO.File]::WriteAllText("$d\build-manifest.json",($built|ConvertTo-Json -Depth 4),(New-Object Text.UTF8Encoding($false)))
$built|ForEach-Object{"{0} {1} {2}" -f $_.arch,$_.module,$_.module_sha256}
