# Copy the built c32-wave1 modules to D:\DLSSNR-Lab\c32-vec-20260926\payload\<arch> and print old/new hashes.
$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend'
foreach($a in @('gfx1200','gfx1201')){
 $old=(Get-FileHash "$r\vit-proj-n64-production\modules-$a\c32-wave1.hsaco").Hash;$src="$r\c32-vec-production\modules-$a\c32-wave1.hsaco"
 $dst="D:\DLSSNR-Lab\c32-vec-20260926\payload\$a";New-Item -ItemType Directory -Force $dst|Out-Null;Copy-Item $src "$dst\c32-wave1.hsaco" -Force
 "$a old=$old new=$((Get-FileHash "$dst\c32-wave1.hsaco").Hash)"
}
