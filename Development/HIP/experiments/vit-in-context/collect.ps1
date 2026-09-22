$ErrorActionPreference='Stop';$d='D:\DLSSNR-Lab\hip-backend\vit-in-context';$out="$d\evidence"
New-Item -ItemType Directory -Force $out|Out-Null
foreach($case in @('rejected-before-event-sync','rejected-batched-event-sync','1080','prefix-1080','prefix-900','region-1080','region-900')){
 $from="$d\$case";if(!(Test-Path $from)){continue};$to="$out\$case";New-Item -ItemType Directory -Force $to|Out-Null
 foreach($n in @('context.csv','events.csv','prefix.csv','control.csv','telemetry.log','telemetry.err')){if(Test-Path "$from\$n"){Copy-Item "$from\$n" $to -Force}}
 if(Test-Path "$from\run.log"){[IO.File]::WriteAllText("$to\run.log",(Get-Content "$from\run.log" -Raw))}
}
$hashes=@("$d\network-sync.exe","$d\network-immediate.exe","$d\prefix.exe","$d\region.exe",'D:\DLSSNR-Lab\hip-backend\vit-eight-accumulators\modules-u2\deep_fast-packed.hsaco')|ForEach-Object{[pscustomobject]@{path=$_;sha=(Get-FileHash $_).Hash}}
[IO.File]::WriteAllText("$out\artifacts.json",(ConvertTo-Json -InputObject $hashes))
Compress-Archive -Force -Path "$out\*" -DestinationPath "$d\evidence.zip"
