$ErrorActionPreference='Stop';$d='D:\DLSSNR-Lab\hip-backend\network-fixed-shapes'
& "$d\regression.ps1" -Heights 900,1080 -TimingFrames 1000
if($LASTEXITCODE){throw 'Regression failed'}
& "$d\regression.ps1" -ExtraControls
if($LASTEXITCODE){throw 'Extra controls failed'}
