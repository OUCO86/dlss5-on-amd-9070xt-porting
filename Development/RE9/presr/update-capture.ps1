$ErrorActionPreference='Stop'
$g='C:\Program Files (x86)\Steam\steamapps\common\RESIDENT EVIL requiem BIOHAZARD requiem'
$lab='D:\DLSSNR-Lab\re9-presr'
for($i=0;$i -lt 20;$i++){if(!(Get-Process re9 -ErrorAction SilentlyContinue)){break};Start-Sleep -Seconds 1}
if(Get-Process re9 -ErrorAction SilentlyContinue){throw 'Game still running'}
$b="$lab\backups\capture-$(Get-Date -Format yyyyMMdd-HHmmss)"
foreach($relative in @('dxgi.dll','LmxxfNrRuntime.dll','_storage_\dxgi.dll','_storage_\LmxxfNrRuntime.dll')){
 $dest=Join-Path $b $relative
 New-Item -ItemType Directory (Split-Path $dest) -Force|Out-Null
 Copy-Item "$g\$relative" $dest
 $source=if($relative -like '*dxgi.dll'){"$lab\bin\OptiScaler.dll"}else{"$lab\LmxxfNrRuntime.dll"}
 Copy-Item $source "$g\$relative" -Force
 if((Get-FileHash $source).Hash -ne (Get-FileHash "$g\$relative").Hash){throw 'Installed hash mismatch'}
}
"BACKUP $b"
