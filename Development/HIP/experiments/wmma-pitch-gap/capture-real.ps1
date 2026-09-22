$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\wmma-pitch-gap";$folder="$d\real-vit-1080";$tools='C:\Users\lmxxf\Downloads\RadeonDeveloperToolSuite-2026-05-28-1806\RadeonDeveloperToolSuite-2026-05-28-1806'
& "$r\check-idle.ps1"
New-Item -ItemType Directory -Force $folder|Out-Null
$benchargs=@('D:\DLSSNR-Lab\Magpie-DLSS5-AMD-0.23\DLSS5-AMD\native-game-tiled-assets',"$r\network-fixed-shapes\selected-modules","$r\network-timeline\1080\flags.txt","$r\network-timeline\1080\input.f32","$r\network-timeline\1080\expected.f32",'1920','1152')
Remove-Item Env:GPU_GAP_CAPTURE -ErrorAction SilentlyContinue
& "$d\real_vit_counter.exe" @benchargs > "$folder\no-profile.log" 2> "$folder\no-profile.err"
if($LASTEXITCODE){throw 'Real no-profile failed'}
[IO.File]::WriteAllText("$folder\stdin.txt",'')
$args=@('-m','profiling','-p','real_vit_counter','-o',"$folder\trace.rgp",'--rgp-capture-mode','dispatch','--rgp-auto-capture=dispatch:3000:64','--rgp-render-op-count','64','--rgp-counter-collection','--verbose')
$cli=Start-Process "$tools\RadeonDeveloperPanelCLI.exe" -ArgumentList $args -WorkingDirectory $tools -PassThru -RedirectStandardOutput "$folder\cli.log" -RedirectStandardError "$folder\cli.err" -RedirectStandardInput "$folder\stdin.txt"
try{
 Start-Sleep -Seconds 3
 $env:GPU_GAP_CAPTURE='1'
 & "$d\real_vit_counter.exe" @benchargs > "$folder\bench.log" 2> "$folder\bench.err"
 if($LASTEXITCODE){throw 'Real profile failed'}
 Start-Sleep -Seconds 3
}finally{Remove-Item Env:GPU_GAP_CAPTURE -ErrorAction SilentlyContinue;if(!$cli.HasExited){Stop-Process -Id $cli.Id -Force}}
if(!(Test-Path "$folder\trace.rgp")){throw 'No real trace'}
foreach($log in 'bench.log','no-profile.log'){
 if(@(Get-Content "$folder\$log"|Select-String 'RAW frame=.+ bitdiff=0').Count -ne 2){throw "Real output mismatch $log"}
 if(!(Get-Content "$folder\$log"|Select-String 'REAL_TARGET vit_expand_blocked_fp8_frag_bytein repeats=10000')){throw 'Wrong real target'}
}
Get-Content "$folder\bench.log"
