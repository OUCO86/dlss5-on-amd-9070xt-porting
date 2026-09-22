$ErrorActionPreference='Stop';$d='D:\DLSSNR-Lab\hip-backend\vit-repeat-context';$out="$d\evidence"
New-Item -ItemType Directory -Force $out|Out-Null
foreach($prefix in '','concentrated-','pilot-clones-','clones-'){foreach($height in 1080,900){$to="$out\$prefix$height";New-Item -ItemType Directory -Force $to|Out-Null;foreach($n in 'repeat.csv','telemetry.log','telemetry.err'){Copy-Item "$d\$prefix$height\$n" $to -Force};[IO.File]::WriteAllText("$to\run.log",(Get-Content "$d\$prefix$height\run.log" -Raw))}}
$hashes=@("$d\network.exe","$d\concentrated.exe","$d\clones-pilot.exe","$d\clones.exe",'D:\DLSSNR-Lab\hip-backend\vit-eight-accumulators\modules-u2\deep_fast-packed.hsaco')|ForEach-Object{[pscustomobject]@{path=$_;sha=(Get-FileHash $_).Hash}}
[IO.File]::WriteAllText("$out\artifacts.json",(ConvertTo-Json -InputObject $hashes))
Compress-Archive -Force -Path "$out\*" -DestinationPath "$d\evidence.zip"
