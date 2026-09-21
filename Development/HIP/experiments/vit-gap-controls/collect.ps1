$ErrorActionPreference='Stop';$d='D:\DLSSNR-Lab\hip-backend\vit-gap-controls';$out="$d\evidence"
New-Item -ItemType Directory -Force $out|Out-Null
foreach($prefix in '','repeat-','prime-'){foreach($height in 900,1080){
 $from="$d\$prefix$height-expand";$to="$out\$prefix$height-expand";New-Item -ItemType Directory -Force $to|Out-Null
 Copy-Item "$from\schedule.csv","$from\telemetry.log","$from\telemetry.err" $to
 [IO.File]::WriteAllText("$to\run.log",(Get-Content "$from\run.log" -Raw))
}
}
& "$d\occupancy.exe" "$d\modules\deep_fast-packed.hsaco" > "$d\occupancy.log"
if($LASTEXITCODE){throw 'Occupancy failed'}
[IO.File]::WriteAllText("$out\occupancy.log",(Get-Content "$d\occupancy.log" -Raw))
$hashes=@("$d\kernel.hip","$d\pure.exe","$d\pure-filter.exe","$d\prime.exe","$d\occupancy.exe","$d\gfx1200.hsaco","$d\modules\deep_fast-packed.hsaco")|ForEach-Object{[pscustomobject]@{path=$_;sha=(Get-FileHash $_).Hash}}
[IO.File]::WriteAllText("$out\artifacts.json",(ConvertTo-Json -InputObject $hashes))
Compress-Archive -Force -Path "$out\*" -DestinationPath "$d\evidence.zip"
