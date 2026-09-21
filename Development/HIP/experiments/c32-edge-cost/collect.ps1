$ErrorActionPreference='Stop';$d='D:\DLSSNR-Lab\hip-backend\c32-edge-cost';$out="$d\evidence"
New-Item -ItemType Directory -Force $out|Out-Null
foreach($height in 900,1080){foreach($target in 'prefix','chain','post'){
 $from="$d\$height-$target";if(!(Test-Path "$from\phase.csv")){continue}
 $to="$out\$height-$target";New-Item -ItemType Directory -Force $to|Out-Null
 Copy-Item "$from\phase.csv" $to
 [IO.File]::WriteAllText("$to\run.log",(Get-Content "$from\run.log" -Raw))
}}
$artifacts=@("$d\kernel.hip","$d\pure.exe","$d\gfx1200.hsaco","$d\modules\c32_fused_ffn_attention-packed.hsaco")|ForEach-Object{[pscustomobject]@{path=$_;sha=(Get-FileHash $_).Hash}}
[IO.File]::WriteAllText("$out\artifacts.json",(ConvertTo-Json -InputObject $artifacts))
Compress-Archive -Force -Path "$out\*" -DestinationPath "$d\evidence.zip"
