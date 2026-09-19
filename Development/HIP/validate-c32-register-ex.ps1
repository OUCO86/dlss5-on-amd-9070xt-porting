$ErrorActionPreference='Stop'
$r='D:\DLSSNR-Lab\hip-backend';$base='D:\DLSSNR-Lab\Magpie-DLSS5-AMD-0.23\DLSS5-AMD'
$work="$r\profile1080";$rows=@()
foreach($height in 720,900,1080){foreach($reset in 0,8){
 $flags=@(Get-Content "$base\native-game-flags.txt"|Where-Object{$_ -notmatch '^DLSS5_(NETWORK_HEIGHT|SHOW_FPS|NOTICE)='})+@("DLSS5_NETWORK_HEIGHT=$height",'DLSS5_SHOW_FPS=0','DLSS5_NOTICE=0')
 $f="$work\check-flags.txt";[IO.File]::WriteAllLines($f,$flags)
 $expected=''
 foreach($variant in 'base','candidate'){
  if(Get-Process SB-Win64-Shipping,Magpie -ErrorAction SilentlyContinue){throw 'Game/Magpie running'}
  $m=if($variant -eq 'base'){"$base\native-game-tiled-assets\HIP"}else{"$r\c32-register-ex-modules"}
  $prefix="$work\regex-check-$height-$reset-$variant"
  & "$r\benchmark1080.exe" "$base\native-game-tiled-assets" $f "$r\live-menu-before.f16" $prefix 24 1 $m $reset 0 > "$prefix.log"
  if($LASTEXITCODE){throw 'Validation runner failed'}
  $csv=@(Import-Csv "$prefix.csv");if($csv.Count -ne 24 -or @($csv|Where-Object{[int]$_.invalid -ne 0 -or $_.checked -ne '1'}).Count){throw 'Missing/nonfinite frame'}
  $hash=(Get-FileHash "$prefix.f16").Hash;$first=(Get-FileHash "$prefix-first.f16").Hash
  if($variant -eq 'base'){$expected=$hash;$expectedFirst=$first}else{if($hash -ne $expected -or $first -ne $expectedFirst){throw 'First/final output mismatch'}}
  $row=[pscustomobject]@{height=$height;reset=$reset;variant=$variant;hash=$hash;first=$first};$rows+=$row;$row|ConvertTo-Json -Compress
 }
}}
$rows|Export-Csv "$work\regex-validation.csv" -NoTypeInformation
