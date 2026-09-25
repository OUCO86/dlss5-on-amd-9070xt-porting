param([ValidateSet('daniel','ours','status')][string]$To='status')
# Swap Stellar Blade between our OptiScaler stack and Daniel's closed v0.4.0 proxy (dxgi.dll).
# Our whole stack (OptiScaler -> fakenvapi/ReShade/addon) is loaded only through dxgi.dll, so renaming it disables all of it.
$ErrorActionPreference='Stop'
$g='C:\Program Files (x86)\Steam\steamapps\common\StellarBlade\SB\Binaries\Win64'
$lab='D:\DLSSNR-Lab\daniel-040'
$OURS='dxgi.dll.ours-optiscaler'
$modSha='D62BE3D8B9FBB3C6C81982C4DDB3DFA00EB9662E3206925CBE5B7E1BC6798B80'
$nvSha='E16BCF15E16E13F527491CDF7845B2FE6521A738D8F7C9C721866A8496E1FC8E'
function Sha($p){(Get-FileHash $p).Hash}
function State{
  $d=Join-Path $g 'dxgi.dll'
  if((Test-Path $d) -and (Sha $d) -eq $modSha){'daniel'}elseif(Test-Path (Join-Path $g $OURS)){'broken'}else{'ours'}
}
if($To -eq 'status'){ "state=$(State)"; Get-ChildItem $g -Filter 'dlssnr*' | Select-Object Name,Length,LastWriteTime; exit }
if(Get-Process SB-Win64-Shipping -ErrorAction SilentlyContinue){throw 'game running'}
if($To -eq 'daniel'){
  if((State) -ne 'ours'){throw "state is $(State), expected ours"}
  if((Sha "$lab\mod.dll") -ne $modSha -or (Sha "$lab\nvngx_dlssnr.dll") -ne $nvSha){throw 'source hash mismatch'}
  Rename-Item (Join-Path $g 'dxgi.dll') $OURS
  Copy-Item "$lab\mod.dll" (Join-Path $g 'dxgi.dll')
  if(!(Test-Path (Join-Path $g 'nvngx_dlssnr.dll'))){Copy-Item "$lab\nvngx_dlssnr.dll" $g}
  if(!(Test-Path (Join-Path $g 'dlssnr_on_amd.ini'))){Copy-Item "$lab\dlssnr_on_amd.ini" $g}
  if((Sha (Join-Path $g 'dxgi.dll')) -ne $modSha){throw 'install verify failed'}
  "SWITCHED to daniel 0.4.0"
}else{
  if((State) -ne 'daniel'){throw "state is $(State), expected daniel"}
  Remove-Item (Join-Path $g 'dxgi.dll')
  Rename-Item (Join-Path $g $OURS) 'dxgi.dll'
  "SWITCHED to ours (daniel ini/nvngx/logs left in place, inert without his dxgi.dll)"
}
