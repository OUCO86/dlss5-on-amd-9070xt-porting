$ErrorActionPreference='Stop'
$g='C:\Program Files (x86)\Steam\steamapps\common\RESIDENT EVIL requiem BIOHAZARD requiem';$l='D:\DLSSNR-Lab\re9-presr'
if(Get-Process re9 -ErrorAction SilentlyContinue){throw 'Game is running'}
$b="$l\backups\exposure-$(Get-Date -Format yyyyMMdd-HHmmss)"
$files=@('LmxxfNrRuntime.dll','_storage_\LmxxfNrRuntime.dll','OptiScaler.ini','_storage_\OptiScaler.ini','DLSS5-AMD\native-game-tiled-assets\native_codec_encode.hlsl','DLSS5-AMD\native-game-tiled-assets\native_codec_decode.hlsl')
foreach($f in $files){$dest=Join-Path $b $f;New-Item -ItemType Directory (Split-Path $dest) -Force|Out-Null;Copy-Item "$g\$f" $dest}
$files|ConvertTo-Json|Set-Content "$b\files.json"
foreach($d in @($g,"$g\_storage_")){
 Copy-Item "$l\LmxxfNrRuntime-exposure.dll" "$d\LmxxfNrRuntime.dll" -Force
 $ini=[IO.File]::ReadAllText("$d\OptiScaler.ini")
 $ini=$ini -replace '(?m)^ColourStrength=[^\r\n]*','ColourStrength=1.0'
 $ini=$ini -replace '(?m)^TransferStrength=[^\r\n]*','TransferStrength=1.0'
 $ini=[regex]::Replace($ini,'(?ms)(^\[DlssNr\]\r?\n)(.*?)(?=^\[|\z)',{param($m) $m.Groups[1].Value+([regex]::Replace($m.Groups[2].Value,'(?m)^Enabled=[^\r\n]*','Enabled=true'))})
 [IO.File]::WriteAllText("$d\OptiScaler.ini",$ini)
}
foreach($n in @('native_codec_encode.hlsl','native_codec_decode.hlsl')){Copy-Item "$l\shaders\$n" "$g\DLSS5-AMD\native-game-tiled-assets\$n" -Force}
foreach($f in $files){$hash=(Get-FileHash "$g\$f").Hash;"$f $hash"}
"BACKUP $b"
