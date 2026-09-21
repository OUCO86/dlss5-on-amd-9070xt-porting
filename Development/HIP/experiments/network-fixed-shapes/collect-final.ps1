$ErrorActionPreference='Stop';$d='D:\DLSSNR-Lab\hip-backend\network-fixed-shapes';$out="$d\final-evidence"
New-Item -ItemType Directory -Force $out|Out-Null
foreach($height in 900,1080){
 $from="$d\decoder-repeat-$height";$to="$out\decoder-repeat-$height";New-Item -ItemType Directory -Force $to|Out-Null
 Copy-Item "$from\network.csv","$from\telemetry.log","$from\telemetry.err" $to
 [IO.File]::WriteAllText("$to\run.log",(Get-Content "$from\run.log" -Raw))
}
foreach($height in 900,1080){
 $to="$out\raw-$height";New-Item -ItemType Directory -Force $to|Out-Null
 [IO.File]::WriteAllText("$to\run.log",(Get-Content "$d\raw-$height\run.log" -Raw))
}
$checks=@()
foreach($dir in Get-ChildItem "$d\regression" -Directory){
 $to="$out\regression\$($dir.Name)";New-Item -ItemType Directory -Force $to|Out-Null
 Copy-Item "$($dir.FullName)\rgb.csv","$($dir.FullName)\flags.txt" $to
 [IO.File]::WriteAllText("$to\run.log",(Get-Content "$($dir.FullName)\run.log" -Raw))
 foreach($file in Get-ChildItem $dir.FullName -Filter '*.f16'){$checks+=[pscustomobject]@{case=$dir.Name;file=$file.Name;bytes=$file.Length;sha=(Get-FileHash $file.FullName).Hash}}
}
[IO.File]::WriteAllText("$out\rgb-hashes.json",(ConvertTo-Json -InputObject $checks))
$files=@("$d\raw-check.exe","$d\selected-packed.hip","$d\selected-unpacked.hip","$d\network-repeat.exe")+@(Get-ChildItem "$d\selected-gfx1200\*.hsaco"|ForEach-Object{$_.FullName})+@("$d\selected-modules\deep_fast-packed.hsaco","$d\selected-modules\deep_fast.hsaco")
$hashes=$files|ForEach-Object{[pscustomobject]@{path=$_;sha=(Get-FileHash $_).Hash}}
[IO.File]::WriteAllText("$out\selected-artifacts.json",(ConvertTo-Json -InputObject $hashes))
Compress-Archive -Force -Path "$out\*" -DestinationPath "$d\final-evidence.zip"
