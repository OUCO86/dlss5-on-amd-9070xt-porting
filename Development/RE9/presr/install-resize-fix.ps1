param([string]$RestoreBackup='')
$ErrorActionPreference='Stop'
$g='C:\Program Files (x86)\Steam\steamapps\common\RESIDENT EVIL requiem BIOHAZARD requiem'
$l='D:\DLSSNR-Lab\re9-presr';$src="$l\resize-candidate"
function Closed {if(Get-Process re9 -ErrorAction SilentlyContinue){throw 'RE9 is running; no replacement allowed'}}
Closed
if($RestoreBackup){$m=Get-Content "$RestoreBackup\manifest.json" -Raw|ConvertFrom-Json;foreach($f in $m.files){$p=Join-Path $g $f.path;if($f.existed){Copy-Item (Join-Path $RestoreBackup $f.path) $p -Force}else{Remove-Item $p -ErrorAction SilentlyContinue}};"RESTORED $RestoreBackup";exit}
$expected=@{'dxgi.dll'='0ef102295a759b51c0c7cba6b8eedb455e9759f5a2b7f9b96309e030c6cd0035';'LmxxfNrRuntime.dll'='1b51069c38095988f17403366ac09c1c2e047b28423c7385e669023cf42fbacf'}
$sources=@{'dxgi.dll'="$src\bin\OptiScaler.dll";'LmxxfNrRuntime.dll'="$src\LmxxfNrRuntime.dll"}
foreach($n in $expected.Keys){if((Get-FileHash $sources[$n]).Hash -ne $expected[$n]){throw "Candidate hash mismatch $n"}}
$preserve=@('OptiScaler.ini','_storage_\OptiScaler.ini','config.ini','DLSS5-AMD\native-game-tiled-assets\native_codec_encode.hlsl','DLSS5-AMD\native-game-tiled-assets\native_codec_decode.hlsl')
$unchanged=@{};foreach($p in $preserve){if(Test-Path "$g\$p"){$unchanged[$p]=(Get-FileHash "$g\$p").Hash}}
$b="$l\backups\resize-$(Get-Date -Format yyyyMMdd-HHmmss-fff)"
$files=@(foreach($prefix in @('','_storage_\')){foreach($n in @('dxgi.dll','LmxxfNrRuntime.dll')){$relative=$prefix+$n;$p=Join-Path $g $relative;$exists=Test-Path $p;$hash=$null;if($exists){$hash=(Get-FileHash $p).Hash;$dest=Join-Path $b $relative;New-Item -ItemType Directory (Split-Path $dest) -Force|Out-Null;Copy-Item $p $dest;if((Get-FileHash $dest).Hash -ne $hash){throw 'Backup verification failed'}};[pscustomobject]@{path=$relative;name=$n;existed=$exists;before=$hash;after=$expected[$n]}}})
$m=[pscustomobject]@{source_commit='74b8a67';backup=$b;files=$files;preserved=$unchanged}
$m|ConvertTo-Json -Depth 5|Set-Content "$b\manifest.json"
try{
 Closed
 foreach($f in $files){Copy-Item $sources[$f.name] (Join-Path $g $f.path) -Force;if((Get-FileHash (Join-Path $g $f.path)).Hash -ne $f.after){throw 'Installed hash mismatch'}}
 foreach($p in $unchanged.Keys){if((Get-FileHash "$g\$p").Hash -ne $unchanged[$p]){throw "Unexpected configuration/shader change $p"}}
 $m|ConvertTo-Json -Depth 5|Set-Content "$l\resize-installed.json"
 "INSTALLED 4 verified DLLs; configuration and shaders preserved; BACKUP $b"
}catch{foreach($f in $files){$p=Join-Path $g $f.path;if($f.existed){Copy-Item (Join-Path $b $f.path) $p -Force}else{Remove-Item $p -ErrorAction SilentlyContinue}};throw}
