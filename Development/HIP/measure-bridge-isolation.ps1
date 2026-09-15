$ErrorActionPreference='Stop'
$r='D:\DLSSNR-Lab\hip-backend'
if(Get-Process SB-Win64-Shipping -ErrorAction SilentlyContinue){throw 'Game running'}
& "$r\benchmark_bridge_isolate.exe" "$r\..\network-720p\DLSS5-AMD\native-game-tiled-assets" "$r\rebind-async-flags.txt" "$r\live-menu-before.f16" "$r\bridge-isolate" 40 0 "$r\prefix-direct-input-release-modules" 0 1 > "$r\bridge-isolate.log"
if($LASTEXITCODE){Get-Content "$r\bridge-isolate.log" -Tail 8;throw 'Isolation failed'}
if(Get-Process SB-Win64-Shipping -ErrorAction SilentlyContinue){throw 'Game started'}
$rows=@(Import-Csv "$r\bridge-isolate.csv"|Where-Object{[int]$_.frame -ge 5})
$t=@($rows|ForEach-Object{[double]$_.wall_ms}|Sort-Object)
Write-Output "FULL_FRAME median_ms=$($t[[int]($t.Count/2)]) temporal=0 edges_only=1"
Get-Content "$r\bridge-isolate.log"|Select-String 'BRIDGE_ISOLATE|BRIDGE_FULL_AFTER'
