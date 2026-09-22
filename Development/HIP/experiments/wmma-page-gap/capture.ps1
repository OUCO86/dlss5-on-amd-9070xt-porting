$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\wmma-page-gap";$tools='C:\Users\lmxxf\Downloads\RadeonDeveloperToolSuite-2026-05-28-1806\RadeonDeveloperToolSuite-2026-05-28-1806'
foreach($span in 64){foreach($pitch in 0,1024,2048){
 & "$r\check-idle.ps1"
 $folder="$d\counter-$span-$pitch";New-Item -ItemType Directory -Force $folder|Out-Null
 [IO.File]::WriteAllText("$folder\stdin.txt",'')
 $args=@('-m','profiling','-p','page_counter','-o',"$folder\trace.rgp",'--rgp-capture-mode','dispatch','--rgp-auto-capture=dispatch:3000:64','--rgp-render-op-count','64','--rgp-counter-collection','--verbose')
 $cli=Start-Process "$tools\RadeonDeveloperPanelCLI.exe" -ArgumentList $args -WorkingDirectory $tools -PassThru -RedirectStandardOutput "$folder\cli.log" -RedirectStandardError "$folder\cli.err" -RedirectStandardInput "$folder\stdin.txt"
 try{
  Start-Sleep -Seconds 3
  & "$d\page_counter.exe" "$d\gfx1201.hsaco" $span $pitch > "$folder\bench.log" 2> "$folder\bench.err"
  if($LASTEXITCODE){throw 'Counter replay failed'}
  Start-Sleep -Seconds 3
 }finally{if(!$cli.HasExited){Stop-Process -Id $cli.Id -Force}}
 if(!(Test-Path "$folder\trace.rgp")){throw 'No RGP trace'}
 if(@(Get-Content "$folder\bench.log"|Select-String 'CHECK .+ bad=0').Count -ne 3){throw 'Captured output failed'}
 [pscustomobject]@{span=$span;pitch=$pitch;trace_bytes=(Get-Item "$folder\trace.rgp").Length;checks=3}|ConvertTo-Json -Compress
}}
