param([int[]]$Tokens=@(640,400),[switch]$Extended,[switch]$Multi)
$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\wmma-width-gap"
foreach($tokens in $Tokens){
 & "$r\check-idle.ps1"
 $env:GPU_GAP_CONDITION='1';$prefix=if($Multi){"multi-"}elseif($Extended){"extended-"}else{""};$exe=if($Multi){"$d\bench-multi.exe"}elseif($Extended){"$d\bench-extended.exe"}else{"$d\bench.exe"};$folder="$d\$prefix$tokens";New-Item -ItemType Directory -Force $folder|Out-Null
 $p=Start-Process "$r\clock_observe_telemetry.exe" -ArgumentList '600' -PassThru -NoNewWindow -RedirectStandardOutput "$folder\telemetry.log" -RedirectStandardError "$folder\telemetry.err"
 Push-Location $folder
 try{& $exe "$d\${prefix}gfx1201.hsaco" $tokens > run.log;if($LASTEXITCODE){throw 'Pitch experiment failed'};Get-Content run.log}finally{Pop-Location;if(!$p.HasExited){Stop-Process -Id $p.Id -Force}}
}
Remove-Item Env:GPU_GAP_CONDITION -ErrorAction SilentlyContinue
