param([int[]]$Tokens=@(640,400),[switch]$Conditioned)
$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\wmma-feed-gap"
foreach($tokens in $Tokens){
 & "$r\check-idle.ps1"
 $folder=if($Conditioned){"$d\conditioned-$tokens"}else{"$d\masked-$tokens"};New-Item -ItemType Directory -Force $folder|Out-Null
 $p=Start-Process "$r\clock_observe_telemetry.exe" -ArgumentList '600' -PassThru -NoNewWindow -RedirectStandardOutput "$folder\telemetry.log" -RedirectStandardError "$folder\telemetry.err"
 Push-Location $folder
 $exe=if($Conditioned){$env:GPU_GAP_CONDITION="1";"$d\bench-conditioned.exe"}else{Remove-Item Env:GPU_GAP_CONDITION -ErrorAction SilentlyContinue;"$d\bench-masked.exe"}
 try{& $exe "$d\masked-gfx1201.hsaco" $tokens > run.log;if($LASTEXITCODE){throw "Feed experiment failed $tokens"};Get-Content run.log}finally{Pop-Location;if(!$p.HasExited){Stop-Process -Id $p.Id -Force}}
}

Remove-Item Env:GPU_GAP_CONDITION -ErrorAction SilentlyContinue
