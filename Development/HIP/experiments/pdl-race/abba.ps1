# PDL=1 vs PDL=0 on current production (prod8 + wave-owned, C512_M32=0): full NativeGameFrame replay, 1000 frames per slot,
# first 200 dropped, order A B B A per round. Output <out>\abba.csv (height,round,slot,pdl,mean_ms).
param([int]$Rounds=3,[int[]]$Heights=@(900,1080),[int]$Frames=1000,[string]$Out='D:\DLSSNR-Lab\hip-backend\pdl-race\abba')
$ErrorActionPreference='Stop'
$r='D:\DLSSNR-Lab\hip-backend';$root="$r\c512-m32-production";$a='D:\DLSSNR-Lab\Magpie-DLSS5-AMD-0.23\DLSS5-AMD'
New-Item -ItemType Directory -Force $Out|Out-Null;$csv="$Out\abba.csv";if(!(Test-Path $csv)){'height,round,slot,pdl,mean_ms'|Set-Content $csv}
foreach($h in $Heights){foreach($k in 1..$Rounds){$slot=0;foreach($pdl in 1,0,0,1){
 & "$r\check-idle.ps1" | Out-Null
 $dir="$Out\w";Remove-Item -Recurse -Force $dir -ErrorAction SilentlyContinue;New-Item -ItemType Directory -Force $dir|Out-Null
 $flags=@(Get-Content "$root\runtime-regression\time-$h-0\flags.txt"|Where-Object{$_ -notmatch '^DLSS5_HIP_(C512_M32|PDL)='})+@('DLSS5_HIP_C512_M32=0',"DLSS5_HIP_PDL=$pdl")
 [IO.File]::WriteAllLines("$dir\flags.txt",$flags)
 & "$root\benchmark.exe" "$a\native-game-tiled-assets" "$dir\flags.txt" "$r\live-menu-before.f16" "$dir\rgb" $Frames 0 "$root\modules-gfx1201" 0 1 0 0 > "$dir\run.log"
 if($LASTEXITCODE){throw "replay failed $h $k $pdl"}
 $mean=(Import-Csv "$dir\rgb.csv"|Where-Object{[int]$_.frame -ge 200}|Measure-Object wall_ms -Average).Average
 "$h,$k,$slot,$pdl,$([math]::Round($mean,5))"|Add-Content $csv;$slot++
}}}
"DONE"
