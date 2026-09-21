param([switch]$Collect)
$ErrorActionPreference='Stop'
$g='C:\Program Files (x86)\Steam\steamapps\common\RESIDENT EVIL requiem BIOHAZARD requiem'
if(!$Collect){
 if(!(Get-Process re9 -ErrorAction SilentlyContinue)){throw 'RE9 is not running'}
 Set-Content "$g\_storage_\capture-colour.request" 'same-frame colour diagnostic'
 'CAPTURE_REQUESTED';exit
}
$latest=Get-ChildItem "$g\_storage_" -Directory -Filter 'colour-capture-*'|Sort-Object LastWriteTime -Descending|Select-Object -First 1
if(!$latest -or !(Test-Path "$($latest.FullName)\result.json")){throw 'Capture not completed yet'}
$dest='D:\DLSSNR-Lab\re9-presr\'+$latest.Name
Copy-Item $latest.FullName $dest -Recurse -Force
$dest
Get-Content "$dest\frame.json"
