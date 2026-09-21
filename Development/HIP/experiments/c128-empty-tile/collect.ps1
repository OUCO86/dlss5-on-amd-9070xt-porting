param([string]$Experiment="c128-empty-tile")
$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\${Experiment}-results";$out="$r\${Experiment}-evidence-final"
New-Item -ItemType Directory -Force $out|Out-Null
$checks=@()
foreach($dir in Get-ChildItem $d -Directory){
 if($dir.Name -like "diag-*"){continue}
 $dest="$out\$($dir.Name)";New-Item -ItemType Directory -Force $dest|Out-Null
 Copy-Item "$($dir.FullName)\rgb.csv","$($dir.FullName)\flags.txt" $dest
 $text=Get-Content "$($dir.FullName)\run.log" -Raw
 [IO.File]::WriteAllText("$dest\run.log",$text)
 foreach($f in Get-ChildItem $dir.FullName -Filter '*.f16'){$checks+= [pscustomobject]@{tag=$dir.Name;file=$f.Name;sha=(Get-FileHash $f.FullName).Hash}}
}
foreach($f in Get-ChildItem $d -Filter 'kernel-*.log'){[IO.File]::WriteAllText("$out\$($f.Name)",(Get-Content $f.FullName -Raw))}
[IO.File]::WriteAllText("$out\hashes.json",(ConvertTo-Json -Depth 4 -InputObject $checks))
$runner=if($Experiment -eq "c128-hybrid-reuse"){"benchmark_c128_m32.exe"}else{"benchmark_main_reuse.exe"}
$artifacts=@("$r\${Experiment}-modules\multihead-fast-padded-wave-packed.hsaco","$r\${Experiment}-gfx1200.hsaco","$r\$runner","$r\benchmark_main_reuse.exe","$r\post-head-shared-input-modules\multihead-fast-padded-wave-packed.hsaco")|ForEach-Object{[pscustomobject]@{path=$_;sha=(Get-FileHash $_).Hash}}
[IO.File]::WriteAllText("$out\artifacts.json",(ConvertTo-Json -InputObject $artifacts))
Compress-Archive -Force -Path "$out\*" -DestinationPath "$r\${Experiment}-evidence.zip"
