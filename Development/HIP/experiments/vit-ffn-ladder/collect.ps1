$ErrorActionPreference='Stop';$d='D:\DLSSNR-Lab\hip-backend\vit-ffn-ladder';$out="$d\evidence"
New-Item -ItemType Directory -Force $out|Out-Null
foreach($height in 900,1080){foreach($target in 'expand','contract'){
 $from="$d\$height-$target";if(!(Test-Path "$from\ladder.csv")){continue}
 $to="$out\$height-$target";New-Item -ItemType Directory -Force $to|Out-Null
 Copy-Item "$from\ladder.csv" $to
 [IO.File]::WriteAllText("$to\run.log",(Get-Content "$from\run.log" -Raw))
}}
$artifacts=@("$d\kernel.hip","$d\pure.exe","$d\gfx1200.hsaco","$d\modules\deep_fast-packed.hsaco")|ForEach-Object{[pscustomobject]@{path=$_;sha=(Get-FileHash $_).Hash}}
[IO.File]::WriteAllText("$out\artifacts.json",(ConvertTo-Json -InputObject $artifacts))
Compress-Archive -Force -Path "$out\*" -DestinationPath "$d\evidence.zip"
