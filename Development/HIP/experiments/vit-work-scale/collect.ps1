$ErrorActionPreference='Stop';$d='D:\DLSSNR-Lab\hip-backend\vit-work-scale';$out="$d\evidence"
New-Item -ItemType Directory -Force $out|Out-Null
foreach($folder in '1080-expand','900-expand','streams-1080-expand'){
 $from="$d\$folder";if(!(Test-Path $from)){continue};$to="$out\$folder";New-Item -ItemType Directory -Force $to|Out-Null
 Copy-Item "$from\*.csv","$from\telemetry.log","$from\telemetry.err" $to
 [IO.File]::WriteAllText("$to\run.log",(Get-Content "$from\run.log" -Raw))
}
$hashes=@("$d\kernel.hip","$d\pure.exe","$d\gfx1200.hsaco","$d\modules\deep_fast-packed.hsaco","$d\streams.hip","$d\streams.exe","$d\streams-gfx1200.hsaco","$d\modules-streams\deep_fast-packed.hsaco")|Where-Object{Test-Path $_}|ForEach-Object{[pscustomobject]@{path=$_;sha=(Get-FileHash $_).Hash}}
[IO.File]::WriteAllText("$out\artifacts.json",(ConvertTo-Json -InputObject $hashes))
Compress-Archive -Force -Path "$out\*" -DestinationPath "$d\evidence.zip"
