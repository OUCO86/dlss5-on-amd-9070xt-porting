$ErrorActionPreference='Stop'
$root='D:\DLSSNR-Lab\re9-presr';$src="$root\source";$solution="$src\OptiScaler-DLSSNR-PreSR-Multipass-main"
New-Item -ItemType Directory -Force $src,"$root\bin","$root\obj"|Out-Null
if(!(Test-Path "$solution\OptiScaler\OptiScaler.vcxproj")){& tar.exe -xzf "$root\host-source.tar.gz" -C $src;if($LASTEXITCODE){throw 'Source unpack failed'}}
[IO.File]::WriteAllText("$solution\OptiScaler\resource_build_date.h",('#define VER_BUILD_DATE "20260922_RE9_PreSR"'+"`r`n"))
[IO.File]::WriteAllText("$solution\OptiScaler\resource_build_commit.h",('#define VER_BUILD_COMMIT "8f71f73_lmxxf_staged"'+"`r`n"))
& 'D:\DLSSNR-Lab\build-tools\MSBuild\Current\Bin\MSBuild.exe' "$solution\OptiScaler\OptiScaler.vcxproj" /m:4 /t:Build /p:Configuration=Release /p:Platform=x64 /p:PlatformToolset=v143 /p:WindowsTargetPlatformVersion=10.0.26100.0 /p:PreBuildEventUseInBuild=false /p:PostBuildEventUseInBuild=false "/p:SolutionDir=$solution/" "/p:OutDir=$root/bin/" "/p:IntDir=$root/obj/" /v:minimal /nologo /fl "/flp:logfile=$root/build-host.log;verbosity=normal" > "$root\build-console.log" 2>&1
$code=$LASTEXITCODE
Get-Content "$root\build-console.log" -Tail 35
if($code){throw "Host build failed $code"}
Get-FileHash "$root\bin\OptiScaler.dll"
