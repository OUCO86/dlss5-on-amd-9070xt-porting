$ErrorActionPreference='Stop'
$g='C:\Program Files (x86)\Steam\steamapps\common\RESIDENT EVIL requiem BIOHAZARD requiem'
$l='D:\DLSSNR-Lab\re9-presr'
foreach($scale in @(1,32)){
 Set-Content "$l\capture-colour.request" 'known exposure normalization'
 & "$l\runtime-smoke.exe" "$l\LmxxfNrRuntime-exposure.dll" "$g\DLSS5-AMD\native-game-tiled-assets\HIP" $scale
 if($LASTEXITCODE){throw "Exposure test failed $scale"}
 $latest=Get-ChildItem $l -Directory -Filter 'colour-capture-*'|Sort-Object LastWriteTime -Descending|Select-Object -First 1
 Copy-Item $latest.FullName "$l\exposure-test-$scale" -Recurse -Force
}
