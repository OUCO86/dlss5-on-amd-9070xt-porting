$ErrorActionPreference='Stop'
$root='D:\DLSSNR-Lab\re9-presr';$installer="$root\vs_buildtools.exe";$dest='D:\DLSSNR-Lab\build-tools'
if(Test-Path "$dest\MSBuild\Current\Bin\MSBuild.exe"){'BUILD_TOOLS_PRESENT';exit 0}
$s=Get-AuthenticodeSignature $installer
if($s.Status -ne 'Valid' -or $s.SignerCertificate.Subject -notmatch 'Microsoft Corporation'){throw 'Build Tools signature verification failed'}
$args=@('--quiet','--wait','--norestart','--nocache','--installPath',$dest,'--add','Microsoft.VisualStudio.Workload.VCTools','--add','Microsoft.VisualStudio.Component.VC.Tools.x86.x64','--add','Microsoft.VisualStudio.Component.Windows11SDK.26100')
$p=Start-Process $installer -ArgumentList $args -PassThru -Wait
[IO.File]::WriteAllText("$root\installer-pid.txt",[string]$p.Id)
[IO.File]::WriteAllText("$root\installer-exit.txt",[string]$p.ExitCode)
"BUILD_TOOLS_EXIT code=$($p.ExitCode)"
if($p.ExitCode -notin 0,3010){throw "Build Tools install failed: $($p.ExitCode)"}
