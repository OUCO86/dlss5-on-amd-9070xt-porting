$ErrorActionPreference='Stop';$d='D:\DLSSNR-Lab\hip-backend\vit-eight-accumulators';$out="$d\evidence"
New-Item -ItemType Directory -Force $out|Out-Null
foreach($prefix in '','u2-'){foreach($height in 1080,900){
 $from="$d\$prefix$height-expand";$to="$out\$prefix$height-expand";New-Item -ItemType Directory -Force $to|Out-Null
 Copy-Item "$from\layout.csv","$from\telemetry.log","$from\telemetry.err" $to -Force
 [IO.File]::WriteAllText("$to\run.log",(Get-Content "$from\run.log" -Raw))
}}
& "$d\occupancy.exe" "$d\modules\deep_fast-packed.hsaco" > "$out\occupancy.txt"
if($LASTEXITCODE){throw 'Occupancy failed'}
& "$d\occupancy-u2.exe" "$d\modules-u2\deep_fast-packed.hsaco" > "$out\u2-occupancy.txt"
if($LASTEXITCODE){throw 'U2 occupancy failed'}
foreach($height in 1080,900){
 $from="$d\network-$height";if(!(Test-Path "$from\network.csv")){continue};$to="$out\network-$height";New-Item -ItemType Directory -Force $to|Out-Null
 Copy-Item "$from\network.csv","$from\telemetry.log","$from\telemetry.err" $to -Force
 [IO.File]::WriteAllText("$to\run.log",(Get-Content "$from\run.log" -Raw))
}
$hashes=@("$d\network.exe","$d\kernel.hip","$d\pure.exe","$d\gfx1200.hsaco","$d\modules\deep_fast-packed.hsaco","$d\u2.hip","$d\u2.exe","$d\u2-gfx1200.hsaco","$d\modules-u2\deep_fast-packed.hsaco")|ForEach-Object{[pscustomobject]@{path=$_;sha=(Get-FileHash $_).Hash}}
[IO.File]::WriteAllText("$out\artifacts.json",(ConvertTo-Json -InputObject $hashes))
Compress-Archive -Force -Path "$out\*" -DestinationPath "$d\evidence.zip"
