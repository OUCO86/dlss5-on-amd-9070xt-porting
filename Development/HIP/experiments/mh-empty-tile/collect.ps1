param([ValidateSet('c64','c256')][string]$Variant)
$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\mh-empty-$Variant-results";$out="$r\mh-empty-$Variant-evidence"
New-Item -ItemType Directory -Force $out|Out-Null
$hashes=@()
foreach($dir in Get-ChildItem $d -Directory){
 $dest="$out\$($dir.Name)";New-Item -ItemType Directory -Force $dest|Out-Null
 Copy-Item "$($dir.FullName)\rgb.csv","$($dir.FullName)\flags.txt" $dest
 [IO.File]::WriteAllText("$dest\run.log",(Get-Content "$($dir.FullName)\run.log" -Raw))
 foreach($f in Get-ChildItem $dir.FullName -Filter '*.f16'){$hashes+=[pscustomobject]@{tag=$dir.Name;file=$f.Name;sha=(Get-FileHash $f.FullName).Hash}}
}
foreach($f in Get-ChildItem $d -Filter 'kernel-*.log'){[IO.File]::WriteAllText("$out\$($f.Name)",(Get-Content $f.FullName -Raw))}
[IO.File]::WriteAllText("$out\hashes.json",(ConvertTo-Json -InputObject $hashes))
$artifacts=@("$r\mh-empty-$Variant-modules\multihead-fast-padded-wave-packed.hsaco","$r\mh-empty-$Variant-gfx1200.hsaco","$r\c128-empty-vertical-modules\multihead-fast-padded-wave-packed.hsaco","$r\pure_mh_empty.exe","$r\benchmark_main_reuse.exe")|ForEach-Object{[pscustomobject]@{path=$_;sha=(Get-FileHash $_).Hash}}
[IO.File]::WriteAllText("$out\artifacts.json",(ConvertTo-Json -InputObject $artifacts))
Compress-Archive -Force -Path "$out\*" -DestinationPath "$r\mh-empty-$Variant-evidence.zip"
