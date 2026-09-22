$ErrorActionPreference='Stop';$d='D:\DLSSNR-Lab\hip-backend\wmma-page-gap';$out="$d\evidence"
New-Item -ItemType Directory -Force $out|Out-Null
$to="$out\640";New-Item -ItemType Directory -Force $to|Out-Null;Copy-Item "$d\640\*" $to -Force
foreach($folder in (Get-ChildItem "$d\counter-*" -Directory)){
 $to="$out\$($folder.Name)";New-Item -ItemType Directory -Force $to|Out-Null
 Get-ChildItem $folder.FullName -File|Where-Object {$_.Extension -in '.log','.err'}|ForEach-Object {Copy-Item $_.FullName $to -Force}
}
$files=@('kernel.hip','bench.exe','page_counter.exe','resources.exe','gfx1200.hsaco','gfx1201.hsaco')|ForEach-Object {"$d\$_"}
$files+=@(Get-ChildItem "$d\counter-*\trace.rgp"|ForEach-Object {$_.FullName})
$hashes=$files|ForEach-Object {[pscustomobject]@{path=$_;bytes=(Get-Item $_).Length;sha=(Get-FileHash $_).Hash}}
[IO.File]::WriteAllText("$out\artifacts.json",(ConvertTo-Json -InputObject $hashes))
Compress-Archive -Force -Path "$out\*" -DestinationPath "$d\evidence.zip"
