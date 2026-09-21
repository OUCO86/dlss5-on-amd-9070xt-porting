$ErrorActionPreference='Stop';$d='D:\DLSSNR-Lab\hip-backend\network-fixed-shapes';$out="$d\evidence"
New-Item -ItemType Directory -Force $out|Out-Null
foreach($height in 900,1080){
 $from="$d\network-$height";$to="$out\network-$height";New-Item -ItemType Directory -Force $to|Out-Null
 Copy-Item "$from\network.csv","$from\telemetry.log","$from\telemetry.err" $to
 [IO.File]::WriteAllText("$to\run.log",(Get-Content "$from\run.log" -Raw))
}
$artifacts=@("$d\network.exe","$d\deep.hip","$d\mh.hip","$d\attention.hip","$d\reference.hip")+@(Get-ChildItem "$d\gfx1200\*.hsaco"|ForEach-Object{$_.FullName})+@(Get-ChildItem "$d\modules\*.hsaco"|ForEach-Object{$_.FullName})
$hashes=$artifacts|ForEach-Object{[pscustomobject]@{path=$_;sha=(Get-FileHash $_).Hash}}
[IO.File]::WriteAllText("$out\artifacts.json",(ConvertTo-Json -InputObject $hashes))
Compress-Archive -Force -Path "$out\*" -DestinationPath "$d\evidence.zip"
