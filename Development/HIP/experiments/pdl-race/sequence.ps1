# Reproduce the regression's process order: a "primer" replay (default: 720 motion, C512_M32=1 — the run that preceded the
# one failure) immediately followed by the 900 history base replay; compare the latter with the majority reference.
# Tests whether the outlier depends on what the previous process left in VRAM rather than on PDL.
param([int]$N=20,[int]$Pdl=1,[string]$Out='D:\DLSSNR-Lab\hip-backend\pdl-race\seq',[string]$PrimerSrc='extra-720-motion-True',[int]$PrimerFrames=12,[int]$PrimerTemporal=0,[string]$VictimExtra='')
$ErrorActionPreference='Stop'
$r='D:\DLSSNR-Lab\hip-backend';$root="$r\c512-m32-production";$a='D:\DLSSNR-Lab\Magpie-DLSS5-AMD-0.23\DLSS5-AMD'
$ref="$root\flaky2-pdl1\b1";$refHash=@{};foreach($f in Get-ChildItem $ref -Filter '*frame-*.f16'){$refHash[$f.Name]=(Get-FileHash $f.FullName).Hash}
New-Item -ItemType Directory -Force $Out|Out-Null;$csv="$Out\results.csv";if(!(Test-Path $csv)){'primer,pdl,run,bad,frames'|Set-Content $csv}
foreach($i in 1..$N){
 & "$r\check-idle.ps1" | Out-Null
 if($PrimerSrc -ne 'none'){
  $p="$Out\p";Remove-Item -Recurse -Force $p -ErrorAction SilentlyContinue;New-Item -ItemType Directory -Force $p|Out-Null
  Copy-Item "$root\runtime-regression\$PrimerSrc\flags.txt" "$p\flags.txt"
  & "$root\benchmark-trace.exe" "$a\native-game-tiled-assets" "$p\flags.txt" "$r\live-menu-before.f16" "$p\rgb" $PrimerFrames $PrimerTemporal "$root\modules-gfx1201" 0 0 0 0 > "$p\run.log"
 }
 $dir="$Out\w";Remove-Item -Recurse -Force $dir -ErrorAction SilentlyContinue;New-Item -ItemType Directory -Force $dir|Out-Null
 $flags=@(Get-Content "$root\runtime-regression\extra-900-history-False\flags.txt"|Where-Object{$_ -notmatch '^DLSS5_HIP_(C512_M32|PDL)='})+@('DLSS5_HIP_C512_M32=0',"DLSS5_HIP_PDL=$Pdl")
 if($VictimExtra){$flags+=$VictimExtra.Split(';')}
 [IO.File]::WriteAllLines("$dir\flags.txt",$flags)
 & "$root\benchmark-trace.exe" "$a\native-game-tiled-assets" "$dir\flags.txt" "$r\live-menu-before.f16" "$dir\rgb" 12 1 "$root\modules-gfx1201" 0 0 0 0 > "$dir\run.log"
 $bad=@(foreach($k in $refHash.Keys|Sort-Object){if((Get-FileHash "$dir\$k").Hash -ne $refHash[$k]){$k -replace '.*frame-','' -replace '\.f16',''}})
 "$PrimerSrc,$Pdl,$i,$($bad.Count),$($bad -join ' ')"|Add-Content $csv
 if($bad.Count){Copy-Item -Recurse $dir "$Out\bad-$i"}
}
"DONE"
