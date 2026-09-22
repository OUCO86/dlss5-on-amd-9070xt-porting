$ErrorActionPreference='Stop';$d='D:\DLSSNR-Lab\hip-backend\wmma-pitch-gap';$out="$d\evidence"
New-Item -ItemType Directory -Force $out|Out-Null
$to="$out\640";New-Item -ItemType Directory -Force $to|Out-Null;Copy-Item "$d\640\*" $to -Force
$folders=@(Get-ChildItem "$d\counter-*" -Directory)+@(Get-Item "$d\real-vit-1080")
foreach($folder in $folders){
 $to="$out\$($folder.Name)";New-Item -ItemType Directory -Force $to|Out-Null
 Get-ChildItem $folder.FullName -File|Where-Object {$_.Extension -in '.log','.err'}|ForEach-Object {Copy-Item $_.FullName $to -Force}
}
$files=@('kernel.hip','bench.exe','pitch_counter.exe','resources.exe','real_vit_counter.exe','gfx1200.hsaco','gfx1201.hsaco')|ForEach-Object {"$d\$_"}
$files+=@(Get-ChildItem "$d\counter-*\trace.rgp"|ForEach-Object {$_.FullName})
$files+="$d\real-vit-1080\trace.rgp"
$files+="D:\DLSSNR-Lab\hip-backend\network-fixed-shapes\selected-modules\deep_fast-packed.hsaco"
foreach($n in 'flags.txt','input.f32','expected.f32'){$files+="D:\DLSSNR-Lab\hip-backend\network-timeline\1080\$n"}
$hashes=$files|ForEach-Object {[pscustomobject]@{path=$_;bytes=(Get-Item $_).Length;sha=(Get-FileHash $_).Hash}}
[IO.File]::WriteAllText("$out\artifacts.json",(ConvertTo-Json -InputObject $hashes))
Compress-Archive -Force -Path "$out\*" -DestinationPath "$d\evidence.zip"
