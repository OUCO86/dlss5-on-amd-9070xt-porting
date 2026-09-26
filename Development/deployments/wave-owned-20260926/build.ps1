param([string[]]$Architectures=@('gfx1200','gfx1201'))
$ErrorActionPreference='Stop';$d=Split-Path -Parent $MyInvocation.MyCommand.Path;$r='D:\DLSSNR-Lab\hip-backend'
& "$r\check-idle.ps1"
$built=@()
foreach($arch in $Architectures){
 $base=if($arch -eq 'gfx1201'){"$r\network-fixed-shapes\prod8-modules"}elseif($arch -eq 'gfx1200'){"$r\network-fixed-shapes\prod8-gfx1200"}else{throw 'Unsupported architecture'}
 $m="$d\modules-$arch";New-Item -ItemType Directory -Force $m | Out-Null;Copy-Item "$base\*.hsaco" $m
 foreach($name in 'c32-wave1','c64-wave2'){
  & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$m\$name.hsaco" "$d\$name.hip" comgr $arch
  if($LASTEXITCODE){throw "Compile failed $arch $name"}
  $built+=@{arch=$arch;module=$name;source_sha256=(Get-FileHash "$d\$name.hip").Hash;module_sha256=(Get-FileHash "$m\$name.hsaco").Hash}
 }
}
[IO.File]::WriteAllText("$d\build-manifest.json",($built|ConvertTo-Json -Depth 4),(New-Object Text.UTF8Encoding($false)))
