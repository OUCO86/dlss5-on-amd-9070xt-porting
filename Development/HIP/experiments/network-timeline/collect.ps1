$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\network-timeline";$out="$d\evidence"
New-Item -ItemType Directory -Force $out|Out-Null
$hashes=@()
foreach($height in 900,1080){
 $f="$d\$height";$dest="$out\$height";New-Item -ItemType Directory -Force $dest|Out-Null
 Copy-Item "$f\timeline.csv","$f\frames.csv","$f\prefix.csv","$f\prefix-baseline.csv","$f\flags.txt" $dest
 foreach($log in 'run.log','dump.log','prefix.log'){[IO.File]::WriteAllText("$dest\$log",(Get-Content "$f\$log" -Raw))}
 foreach($file in 'input.f32','expected.f32','rgb.f16'){$hashes+=[pscustomobject]@{height=$height;file=$file;sha=(Get-FileHash "$f\$file").Hash}}
}
[IO.File]::WriteAllText("$out\hashes.json",(ConvertTo-Json -InputObject $hashes))
$files=@("$d\pure.exe","$d\prefix.exe","$d\dump.exe","$r\mh-empty-c256-modules\c32_fused_ffn_attention-packed.hsaco","$r\mh-empty-c256-modules\multihead-fast-padded-wave-packed.hsaco","$r\mh-empty-c256-modules\deep_fast-packed.hsaco","$r\mh-empty-c256-modules\multihead_fused_attention.hsaco")
$artifacts=$files|ForEach-Object{[pscustomobject]@{path=$_;sha=(Get-FileHash $_).Hash}}
[IO.File]::WriteAllText("$out\artifacts.json",(ConvertTo-Json -InputObject $artifacts))
Compress-Archive -Force -Path "$out\*" -DestinationPath "$d\evidence.zip"
