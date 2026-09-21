$ErrorActionPreference='Stop';$d='D:\DLSSNR-Lab\hip-backend\vit-compute-density';$out="$d\evidence"
New-Item -ItemType Directory -Force $out|Out-Null
foreach($prefix in '', 'seeded-', 'uniform-'){foreach($height in 1080,900){
 $from="$d\$prefix$height-expand";$to="$out\$prefix$height-expand";New-Item -ItemType Directory -Force $to|Out-Null
 Copy-Item "$from\schedule.csv","$from\telemetry.log","$from\telemetry.err" $to
 [IO.File]::WriteAllText("$to\run.log",(Get-Content "$from\run.log" -Raw))
}
}
$hashes=@("$d\kernel.hip","$d\pure.exe","$d\gfx1200.hsaco","$d\modules\deep_fast-packed.hsaco","$d\seeded.hip","$d\seeded-gfx1200.hsaco","$d\modules-seeded\deep_fast-packed.hsaco","$d\uniform.hip","$d\uniform-gfx1200.hsaco","$d\modules-uniform\deep_fast-packed.hsaco")|ForEach-Object{[pscustomobject]@{path=$_;sha=(Get-FileHash $_).Hash}}
[IO.File]::WriteAllText("$out\artifacts.json",(ConvertTo-Json -InputObject $hashes))
Compress-Archive -Force -Path "$out\*" -DestinationPath "$d\evidence.zip"
