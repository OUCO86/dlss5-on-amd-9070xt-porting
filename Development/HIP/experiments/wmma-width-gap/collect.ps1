$ErrorActionPreference='Stop';$d='D:\DLSSNR-Lab\hip-backend\wmma-width-gap';$out="$d\evidence"
New-Item -ItemType Directory -Force $out|Out-Null
foreach($name in '640','400','extended-640','extended-400','multi-640','multi-400','fixed-grid','fixed-rows'){
 $to="$out\$name";New-Item -ItemType Directory -Force $to|Out-Null;Copy-Item "$d\$name\*" $to -Force
}
foreach($folder in (Get-ChildItem "$d\counter-*" -Directory)){
 $to="$out\$($folder.Name)";New-Item -ItemType Directory -Force $to|Out-Null
 Get-ChildItem $folder.FullName -File|Where-Object {$_.Extension -in '.log','.err'}|ForEach-Object {Copy-Item $_.FullName $to -Force}
}
$files=@('kernel.hip','extended.hip','multi.hip','rows.hip','bench.exe','bench-extended.exe','bench-multi.exe','bench-grid.exe','bench-rows.exe','numeric.exe','numeric-extended.exe','numeric-multi.exe','width_counter.exe','gfx1200.hsaco','gfx1201.hsaco','extended-gfx1200.hsaco','extended-gfx1201.hsaco','multi-gfx1200.hsaco','multi-gfx1201.hsaco','rows-gfx1200.hsaco','rows-gfx1201.hsaco')|ForEach-Object {"$d\$_"}
$files+=@(Get-ChildItem "$d\counter-*\trace.rgp"|ForEach-Object {$_.FullName})
$hashes=$files|ForEach-Object {[pscustomobject]@{path=$_;bytes=(Get-Item $_).Length;sha=(Get-FileHash $_).Hash}}
[IO.File]::WriteAllText("$out\artifacts.json",(ConvertTo-Json -InputObject $hashes))
Compress-Archive -Force -Path "$out\*" -DestinationPath "$d\evidence.zip"
