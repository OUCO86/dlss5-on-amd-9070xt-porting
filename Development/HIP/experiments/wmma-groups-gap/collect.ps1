$ErrorActionPreference='Stop';$d='D:\DLSSNR-Lab\hip-backend\wmma-groups-gap';$out="$d\evidence"
New-Item -ItemType Directory -Force $out|Out-Null
foreach($name in '640','uniform-640','order-640'){
 $to="$out\$name";New-Item -ItemType Directory -Force $to|Out-Null;Copy-Item "$d\$name\*" $to -Force
}
foreach($folder in (Get-ChildItem "$d\counter-*" -Directory)){
 $to="$out\$($folder.Name)";New-Item -ItemType Directory -Force $to|Out-Null
 Get-ChildItem $folder.FullName -File|Where-Object {$_.Extension -in '.log','.err'}|ForEach-Object {Copy-Item $_.FullName $to -Force}
}
Copy-Item "$d\numeric-order.log" $out -Force
$files=@('kernel.hip','uniform.hip','order.hip','bench.exe','bench-uniform.exe','bench-order.exe','numeric.exe','numeric-uniform.exe','numeric-order.exe','resources.exe','groups_counter.exe','order_counter.exe','gfx1200.hsaco','gfx1201.hsaco','uniform-gfx1200.hsaco','uniform-gfx1201.hsaco','order-gfx1200.hsaco','order-gfx1201.hsaco')|ForEach-Object {"$d\$_"}
$files+=@(Get-ChildItem "$d\counter-*\trace.rgp"|ForEach-Object {$_.FullName})
$hashes=$files|ForEach-Object {[pscustomobject]@{path=$_;bytes=(Get-Item $_).Length;sha=(Get-FileHash $_).Hash}}
[IO.File]::WriteAllText("$out\artifacts.json",(ConvertTo-Json -InputObject $hashes))
Compress-Archive -Force -Path "$out\*" -DestinationPath "$d\evidence.zip"
