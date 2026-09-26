# Repeat the 900/1080 history NativeGameFrame replay (production: prod8 + wave-owned) N times per configuration and
# compare every frame with a reference run. 900 reference = flaky2-pdl1\b1 (majority of 20+ runs incl. PDL=0; the regression's
# extra-900-history-False is itself the outlier run, frames 8-11 differ).
# Output: <out>\results.csv  (config,height,run,bad_frames,list)
param([string]$RefRoot='D:\DLSSNR-Lab\hip-backend\c512-m32-production\flaky2-pdl1\b1',[string]$Ref1080='D:\DLSSNR-Lab\hip-backend\c512-m32-production\runtime-regression\extra-1080-history-False',[int]$N=50,[int[]]$Heights=@(900),[string[]]$Configs=@('pdl1','pdl0'),[string]$Out='D:\DLSSNR-Lab\hip-backend\pdl-race\rep',[string]$Extra='',[string]$Modules='')
$ErrorActionPreference='Stop'
$r='D:\DLSSNR-Lab\hip-backend';$root="$r\c512-m32-production";$a='D:\DLSSNR-Lab\Magpie-DLSS5-AMD-0.23\DLSS5-AMD'
if(!$Modules){$Modules="$root\modules-gfx1201"}
$exe=if(Test-Path "$r\pdl-race\benchmark-trace.exe"){"$r\pdl-race\benchmark-trace.exe"}else{"$root\benchmark-trace.exe"}
New-Item -ItemType Directory -Force $Out|Out-Null
$csv="$Out\results.csv";if(!(Test-Path $csv)){'config,height,run,bad,frames'|Set-Content $csv}
foreach($h in $Heights){
 $src="$root\runtime-regression\extra-$h-history-False"
 $refDir=if($h -eq 900){$RefRoot}else{$Ref1080}
 $refHash=@{};foreach($f in Get-ChildItem $refDir -Filter '*frame-*.f16'){$refHash[$f.Name]=(Get-FileHash $f.FullName).Hash}
 if($refHash.Count -ne 12){throw "reference $src incomplete"}
 foreach($i in 1..$N){foreach($c in $Configs){
  & "$r\check-idle.ps1" | Out-Null
  $pdl=if($c -eq 'pdl0'){0}else{1}
  $dir="$Out\w";Remove-Item -Recurse -Force $dir -ErrorAction SilentlyContinue;New-Item -ItemType Directory -Force $dir|Out-Null
  $flags=@(Get-Content "$src\flags.txt"|Where-Object{$_ -notmatch '^DLSS5_HIP_(C512_M32|PDL)='})+@('DLSS5_HIP_C512_M32=0',"DLSS5_HIP_PDL=$pdl")
  if($Extra){$flags+=$Extra.Split(';')}
  [IO.File]::WriteAllLines("$dir\flags.txt",$flags)
  & $exe "$a\native-game-tiled-assets" "$dir\flags.txt" "$r\live-menu-before.f16" "$dir\rgb" 12 1 $Modules 0 0 0 0 > "$dir\run.log"
  if($LASTEXITCODE){"$c,$h,$i,ERR,exit$LASTEXITCODE"|Add-Content $csv;continue}
  $bad=@(foreach($k in $refHash.Keys|Sort-Object){$p="$dir\$k";if(!(Test-Path $p) -or (Get-FileHash $p).Hash -ne $refHash[$k]){$k -replace '.*frame-','' -replace '\.f16',''}})
  "$c,$h,$i,$($bad.Count),$($bad -join ' ')"|Add-Content $csv
  if($bad.Count){Copy-Item -Recurse $dir "$Out\bad-$c-$h-$i"}
 }}
}
"DONE"
