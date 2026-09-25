param([int[]]$Heights=@(1080,900),[string]$Table='',[int]$Tests=4,[string]$Modules='modules')
$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\pdl-chain";$assets='D:\DLSSNR-Lab\Magpie-DLSS5-AMD-0.23\DLSS5-AMD\native-game-tiled-assets'
foreach($height in $Heights){
 & "$r\check-idle.ps1"
 $folder="$d\$height-$Modules";New-Item -ItemType Directory -Force $folder|Out-Null
 $w=if($height -eq 900){1600}else{1920};$h=if($height -eq 900){960}else{1152}
 $p=Start-Process "$r\clock_observe_telemetry.exe" -ArgumentList '600' -PassThru -NoNewWindow -RedirectStandardOutput "$folder\telemetry.log" -RedirectStandardError "$folder\telemetry.err"
 Push-Location $folder
 if($Table){$env:DLSS5_PDL_TABLE=$Table}else{Remove-Item Env:DLSS5_PDL_TABLE -ErrorAction SilentlyContinue};$env:DLSS5_PDL_TESTS="$Tests"
 try{& "$d\network.exe" $assets "$d\$Modules" "$r\network-timeline\$height\flags.txt" "$r\network-timeline\$height\input.f32" "$r\network-timeline\$height\expected.f32" $w $h > run.log;if($LASTEXITCODE){throw "pdl chain failed $height"};Get-Content run.log}finally{Pop-Location;if(!$p.HasExited){Stop-Process -Id $p.Id -Force}}
}
