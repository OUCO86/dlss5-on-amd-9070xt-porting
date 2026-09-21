$ErrorActionPreference='Stop';$d='D:\DLSSNR-Lab\hip-backend\gpu-throughput';$out="$d\evidence"
New-Item -ItemType Directory -Force $out|Out-Null
foreach($name in 'initial','dual','repeat-fp8','repeat-fp16','repeat-fp32d'){
 $dest="$out\$name";New-Item -ItemType Directory -Force $dest|Out-Null
 Copy-Item "$d\$name\timing.csv" $dest
 foreach($file in 'run.log','telemetry.log','telemetry.err'){[IO.File]::WriteAllText("$dest\$file",(Get-Content "$d\$name\$file" -Raw))}
}
$artifacts=@("$d\gfx1200.hsaco","$d\gfx1201.hsaco","$d\bench.exe","$d\kernel.hip","C:\Windows\System32\amdhip64_7.dll","C:\Windows\System32\amd_comgr_3.dll")|ForEach-Object{[pscustomobject]@{path=$_;sha=(Get-FileHash $_).Hash;version=(Get-Item $_).VersionInfo.FileVersion}}
[IO.File]::WriteAllText("$out\artifacts.json",(ConvertTo-Json -InputObject $artifacts))
Compress-Archive -Force -Path "$out\*" -DestinationPath "$d\evidence.zip"
