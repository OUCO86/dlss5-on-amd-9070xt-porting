# Print frame-8..11 hash prefixes of every earlier 900-history run, to find which one is the outlier.
$root='D:\DLSSNR-Lab\hip-backend\c512-m32-production'
$dirs=@(Get-ChildItem "$root\runtime-regression" -Directory|Where-Object Name -like 'extra-900-history*')+@(Get-ChildItem "$root\flaky2-pdl1","$root\flaky" -Directory -ErrorAction SilentlyContinue)+@(Get-Item 'D:\DLSSNR-Lab\hip-backend\pdl-race\smoke\w' -ErrorAction SilentlyContinue)
foreach($d in $dirs){
 $h=@(foreach($k in 0,7,8,11){$p="$($d.FullName)\rgb-frame-$k.f16";if(Test-Path $p){(Get-FileHash $p).Hash.Substring(0,8)}else{'--------'}})
 "{0,-60} {1}  {2}" -f $d.FullName.Replace($root,''),($h -join ' '),(Get-Item $d.FullName).LastWriteTime
}
