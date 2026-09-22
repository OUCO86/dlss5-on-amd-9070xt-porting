$ErrorActionPreference='Stop';$d='D:\DLSSNR-Lab\hip-backend\c32-pair-encode';$r='D:\DLSSNR-Lab\hip-backend';$out="$d\evidence"
New-Item -ItemType Directory -Force $out|Out-Null
foreach($folder in (Get-ChildItem $d -Directory|Where-Object {$_.Name -match '^(900|1080|retain-(900|1080)|fused-(900|1080)-.+)$'})){
 $to="$out\$($folder.Name)";New-Item -ItemType Directory -Force $to|Out-Null
 foreach($file in (Get-ChildItem $folder.FullName -File)){Copy-Item $file.FullName $to -Force}
}
$files=@("$d\kernel.hip","$d\retain.hip","$d\network.exe","$d\network-retain.exe","$d\primitive.exe","$d\fused.exe","$d\gfx1200.hsaco","$d\retain-gfx1200.hsaco","$d\modules\c32_fused_ffn_attention-packed.hsaco","$d\modules-retain\c32_fused_ffn_attention-packed.hsaco")
$files+=@(Get-ChildItem "$d\modules\*.hsaco"|ForEach-Object {$_.FullName})
foreach($h in 900,1080){foreach($f in 'flags.txt','input.f32','expected.f32'){$files+="$r\network-timeline\$h\$f"}}
$hashes=$files|Select-Object -Unique|ForEach-Object {[pscustomobject]@{path=$_;sha=(Get-FileHash $_).Hash}}
[IO.File]::WriteAllText("$out\artifacts.json",(ConvertTo-Json -InputObject $hashes))
Compress-Archive -Force -Path "$out\*" -DestinationPath "$d\evidence.zip"
