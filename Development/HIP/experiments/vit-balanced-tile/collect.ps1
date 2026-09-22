$ErrorActionPreference='Stop';$d='D:\DLSSNR-Lab\hip-backend\vit-balanced-tile';$out="$d\evidence"
New-Item -ItemType Directory -Force $out|Out-Null
foreach($prefix in '','layout-'){foreach($height in 1080,900){
 $from="$d\$prefix$height-expand";$to="$out\$prefix$height-expand";New-Item -ItemType Directory -Force $to|Out-Null
 $csv=if($prefix){'layout.csv'}else{'schedule.csv'}
 Copy-Item "$from\$csv","$from\telemetry.log","$from\telemetry.err" $to -Force
 [IO.File]::WriteAllText("$to\run.log",(Get-Content "$from\run.log" -Raw))
}}
& "$d\occupancy.exe" "$d\modules\deep_fast-packed.hsaco" > "$out\occupancy.txt"
if($LASTEXITCODE){throw 'Occupancy query failed'}
foreach($height in 1080,900){
 $from="$d\network-$height";$to="$out\network-$height";New-Item -ItemType Directory -Force $to|Out-Null
 Copy-Item "$from\network.csv","$from\telemetry.log","$from\telemetry.err" $to -Force
 [IO.File]::WriteAllText("$to\run.log",(Get-Content "$from\run.log" -Raw))
}
& "$d\occupancy.exe" "$d\modules-layout\deep_fast-packed.hsaco" layout > "$out\layout-occupancy.txt"
if($LASTEXITCODE){throw 'Layout occupancy query failed'}
$hashes=@("$d\kernel.hip","$d\pure.exe","$d\gfx1200.hsaco","$d\modules\deep_fast-packed.hsaco","$d\network.exe","$d\layout.hip","$d\layout.exe","$d\layout-gfx1200.hsaco","$d\modules-layout\deep_fast-packed.hsaco")|ForEach-Object{[pscustomobject]@{path=$_;sha=(Get-FileHash $_).Hash}}
[IO.File]::WriteAllText("$out\artifacts.json",(ConvertTo-Json -InputObject $hashes))
Compress-Archive -Force -Path "$out\*" -DestinationPath "$d\evidence.zip"
