param([int[]]$Tokens=@(640),[switch]$Uniform)
$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\wmma-groups-gap"
foreach($tokens in $Tokens){
 & "$r\check-idle.ps1"
 $env:GPU_GAP_CONDITION='1';$prefix=if($Uniform){"uniform-"}else{""};$exe=if($Uniform){"$d\bench-uniform.exe"}else{"$d\bench.exe"};$folder="$d\$prefix$tokens";New-Item -ItemType Directory -Force $folder|Out-Null
 $p=Start-Process "$r\clock_observe_telemetry.exe" -ArgumentList '600' -PassThru -NoNewWindow -RedirectStandardOutput "$folder\telemetry.log" -RedirectStandardError "$folder\telemetry.err"
 Push-Location $folder
 try{& $exe "$d\${prefix}gfx1201.hsaco" $tokens > run.log;if($LASTEXITCODE){throw 'Pitch experiment failed'};Get-Content run.log}finally{Pop-Location;if(!$p.HasExited){Stop-Process -Id $p.Id -Force}}
}
Remove-Item Env:GPU_GAP_CONDITION -ErrorAction SilentlyContinue
