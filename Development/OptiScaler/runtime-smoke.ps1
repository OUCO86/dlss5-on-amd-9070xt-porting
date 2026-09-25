$ErrorActionPreference='Stop'
if(Get-Process re9 -ErrorAction SilentlyContinue){throw 'Game running'}
$g='C:\Program Files (x86)\Steam\steamapps\common\RESIDENT EVIL requiem BIOHAZARD requiem'
$env:LMXXF_WEIGHTS_DIR="$g\DLSS5-AMD\native-game-tiled-assets"
$env:LMXXF_SHADER_DIR="$g\DLSS5-AMD\native-game-tiled-assets"
New-Item -ItemType Directory D:\DLSSNR-Lab\re9-presr\shaders -Force|Out-Null
Copy-Item "$g\DLSS5-AMD\native-game-tiled-assets\*.hlsl" D:\DLSSNR-Lab\re9-presr\shaders -Force
Copy-Item "$g\DLSS5-AMD\native-game-tiled-assets\*.hlsli" D:\DLSSNR-Lab\re9-presr\shaders -Force
& D:\DLSSNR-Lab\re9-presr\runtime-smoke.exe D:\DLSSNR-Lab\re9-presr\LmxxfNrRuntime.dll "$g\DLSS5-AMD\native-game-tiled-assets\HIP"
exit $LASTEXITCODE
