$ErrorActionPreference='Stop';$d='D:\DLSSNR-Lab\hip-backend\wmma-feed-gap';$out="$d\evidence"
New-Item -ItemType Directory -Force $out|Out-Null
foreach($name in '640','400','masked-640','masked-400','conditioned-640','conditioned-400','sweep-640'){
 $to="$out\$name";New-Item -ItemType Directory -Force $to|Out-Null
 Copy-Item "$d\$name\*" $to -Force
}
$files=@('kernel.hip','bench.exe','bench-masked.exe','bench-conditioned.exe','bench-sweep.exe','resources.exe','gfx1200.hsaco','gfx1201.hsaco','masked-gfx1200.hsaco','masked-gfx1201.hsaco')
$hashes=$files|ForEach-Object {[pscustomobject]@{path="$d\$_";sha=(Get-FileHash "$d\$_").Hash}}
[IO.File]::WriteAllText("$out\artifacts.json",(ConvertTo-Json -InputObject $hashes))
Compress-Archive -Force -Path "$out\*" -DestinationPath "$d\evidence.zip"
