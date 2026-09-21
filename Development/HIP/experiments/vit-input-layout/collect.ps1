$ErrorActionPreference='Stop';$d='D:\DLSSNR-Lab\hip-backend\vit-input-layout';$out="$d\evidence"
New-Item -ItemType Directory -Force $out|Out-Null
foreach($folder in '1080-expand','900-expand','network-1080','network-900'){
 $from="$d\$folder";if(!(Test-Path $from)){continue};$to="$out\$folder";New-Item -ItemType Directory -Force $to|Out-Null
 Copy-Item "$from\*.csv","$from\telemetry.log","$from\telemetry.err" $to
 [IO.File]::WriteAllText("$to\run.log",(Get-Content "$from\run.log" -Raw))
}
$hashes=@("$d\kernel.hip","$d\pure.exe","$d\network.exe","$d\gfx1200.hsaco","$d\modules\deep_fast-packed.hsaco")|ForEach-Object{[pscustomobject]@{path=$_;sha=(Get-FileHash $_).Hash}}
[IO.File]::WriteAllText("$out\artifacts.json",(ConvertTo-Json -InputObject $hashes))
Compress-Archive -Force -Path "$out\*" -DestinationPath "$d\evidence.zip"
