# Same 900 history replay as repeat.ps1, but with a concurrent GPU "noise" process (a 1080 timing replay of the production
# network) started just before each victim run, to perturb scheduling the way the one observed failure did (its frame times
# jumped to 18-23 ms). Compares PDL=1 vs PDL=0 victims under identical contention.
param([int]$N=30,[string[]]$Configs=@('pdl1','pdl0'),[string]$Out='D:\DLSSNR-Lab\hip-backend\pdl-race\contend',[int]$NoiseFrames=400,[string]$VictimExtra='')
$ErrorActionPreference='Stop'
$r='D:\DLSSNR-Lab\hip-backend';$root="$r\c512-m32-production";$a='D:\DLSSNR-Lab\Magpie-DLSS5-AMD-0.23\DLSS5-AMD'
$ref="$root\flaky2-pdl1\b1";$refHash=@{};foreach($f in Get-ChildItem $ref -Filter '*frame-*.f16'){$refHash[$f.Name]=(Get-FileHash $f.FullName).Hash}
New-Item -ItemType Directory -Force $Out|Out-Null;$csv="$Out\results.csv";if(!(Test-Path $csv)){'config,run,bad,frames,victim_mean_ms'|Set-Content $csv}
$nd="$Out\noise";New-Item -ItemType Directory -Force $nd|Out-Null
$nflags=@(Get-Content "$root\runtime-regression\time-1080-0\flags.txt")
[IO.File]::WriteAllLines("$nd\flags.txt",$nflags)
foreach($i in 1..$N){foreach($c in $Configs){
 & "$r\check-idle.ps1" | Out-Null
 $pdl=if($c -eq 'pdl0'){0}else{1}
 $noise=Start-Process -FilePath "$root\benchmark.exe" -ArgumentList @("`"$a\native-game-tiled-assets`"","`"$nd\flags.txt`"","`"$r\live-menu-before.f16`"","`"$nd\rgb`"",$NoiseFrames,0,"`"$root\modules-gfx1201`"",0,1,0,0) -PassThru -WindowStyle Hidden -RedirectStandardOutput "$nd\run.log"
 Start-Sleep -Milliseconds 2500
 $dir="$Out\w";Remove-Item -Recurse -Force $dir -ErrorAction SilentlyContinue;New-Item -ItemType Directory -Force $dir|Out-Null
 $flags=@(Get-Content "$root\runtime-regression\extra-900-history-False\flags.txt"|Where-Object{$_ -notmatch '^DLSS5_HIP_(C512_M32|PDL)='})+@('DLSS5_HIP_C512_M32=0',"DLSS5_HIP_PDL=$pdl")
 if($VictimExtra){$flags+=$VictimExtra.Split(';')}
 [IO.File]::WriteAllLines("$dir\flags.txt",$flags)
 & "$root\benchmark-trace.exe" "$a\native-game-tiled-assets" "$dir\flags.txt" "$r\live-menu-before.f16" "$dir\rgb" 12 1 "$root\modules-gfx1201" 0 0 0 0 > "$dir\run.log"
 $mean=(Import-Csv "$dir\rgb.csv"|Where-Object{[int]$_.frame -ge 1}|Measure-Object wall_ms -Average).Average
 $bad=@(foreach($k in $refHash.Keys|Sort-Object){if((Get-FileHash "$dir\$k").Hash -ne $refHash[$k]){$k -replace '.*frame-','' -replace '\.f16',''}})
 "$c,$i,$($bad.Count),$($bad -join ' '),$([math]::Round($mean,2))"|Add-Content $csv
 if($bad.Count){Copy-Item -Recurse $dir "$Out\bad-$c-$i"}
 $noise.WaitForExit()
}}
"DONE"
