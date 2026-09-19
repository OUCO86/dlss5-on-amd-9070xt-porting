param([ValidateSet('Package','FixPackage','Release','Install','Restore','Status')][string]$Action='Status',
 [string]$OutputDirectory='D:\給網友打包')
$ErrorActionPreference='Stop'
$lab='D:\DLSSNR-Lab'
$stage="$lab\OptiScaler-DLSS5-AMD-test"
$game='C:\Program Files (x86)\Steam\steamapps\common\StellarBlade\SB\Binaries\Win64'
$backup="$lab\stellarblade-before-optiscaler"
function Closed { if(Get-Process SB-Win64-Shipping -ErrorAction SilentlyContinue){throw 'Close Stellar Blade first.'} }
if($Action -eq 'Release'){
 $source=$stage
 $stage=Join-Path $OutputDirectory 'OptiScaler-DLSS5-AMD-0.23'
 if(Test-Path $stage){throw 'Release staging already exists.'}
 New-Item -ItemType Directory -Force $OutputDirectory|Out-Null
 Copy-Item $source $stage -Recurse
 foreach($n in 'README-TEST.txt','SHA256SUMS-test.txt','setup_windows.bat','setup_linux.sh'){
  Remove-Item "$stage\$n" -ErrorAction SilentlyContinue
 }
 Copy-Item "$lab\package-README-optiscaler.txt" "$stage\README.txt"
 Copy-Item "$lab\OptiScaler-LICENSE.txt" "$stage\OptiScaler-LICENSE.txt"
 $ini=Get-Content "$stage\OptiScaler.ini" -Raw
 if($ini -notmatch '(?m)^Dx12Upscaler=fsr31\s*$'){throw 'Incorrect backend configuration'}
 if((Get-FileHash "$stage\dlss5-amd.addon64").Hash -ne (Get-FileHash "$lab\DLSS5-AMD-0.23\dlss5-amd.addon64").Hash){throw 'Unexpected addon'}
 if(@(Get-ChildItem "$stage\DLSS5-AMD\native-game-tiled-assets\HIP\*.hsaco").Count -ne 24){throw 'Expected 24 HIP modules'}
 if(Get-ChildItem "$stage\DLSS5-AMD\logs" -File|Where-Object{$_.Name -ne '.keep'}){throw 'Package contains runtime logs'}
}
function Archive {
 $sums=if($Action -eq 'Release'){'SHA256SUMS.txt'}else{'SHA256SUMS-test.txt'}
 $lines=@(Get-ChildItem $stage -Recurse -File|Where-Object{$_.Name -ne $sums}|ForEach-Object{(Get-FileHash $_.FullName).Hash+'  '+$_.FullName.Substring($stage.Length+1)})
 $lines|Set-Content "$stage\$sums"
 Add-Type -AssemblyName System.IO.Compression.FileSystem
 if(Test-Path "$stage.zip"){Remove-Item "$stage.zip"}
 [IO.Compression.ZipFile]::CreateFromDirectory($stage,"$stage.zip",[IO.Compression.CompressionLevel]::Fastest,$true)
 $z=[IO.Compression.ZipFile]::OpenRead("$stage.zip")
 try {
  $entries=@{};foreach($e in $z.Entries){$entries[$e.FullName.Replace('\','/')]=$e}
  foreach($line in $lines){
   $name=(Split-Path $stage -Leaf)+'/'+$line.Substring(66).Replace('\','/')
   $entry=$entries[$name];if(!$entry){throw "Archive missing $name"}
   $stream=$entry.Open();$sha=[Security.Cryptography.SHA256]::Create()
   try{$hash=([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-','')}finally{$stream.Dispose();$sha.Dispose()}
   if($hash -ne $line.Substring(0,64)){throw "Archive hash mismatch $name"}
  }
 }finally{$z.Dispose()}
 "ARCHIVE_VERIFIED_FILES=$($lines.Count)"
 Get-FileHash "$stage.zip"
}
if($Action -eq 'Release'){
 Archive
 $hash=(Get-FileHash "$stage.zip").Hash
 [IO.File]::WriteAllText("$stage.zip.sha256",$hash.ToLowerInvariant()+'  '+(Split-Path "$stage.zip" -Leaf)+"`n")
 exit
}
if($Action -eq 'FixPackage'){
 $ini=Get-Content "$stage\OptiScaler.ini" -Raw
 $ini=[regex]::Replace($ini,'(?m)^Dx12Upscaler=.*$','Dx12Upscaler=fsr31')
 $ini=[regex]::Replace($ini,'(?m)^LogLevel=.*$','LogLevel=2')
 [IO.File]::WriteAllText("$stage\OptiScaler.ini",$ini)
 Add-Content "$stage\README-TEST.txt" '0.9.4 requires Dx12Upscaler=fsr31. The bundled ini incorrectly documents ffx; ffx silently selects FSR2.1.2.'
 Archive
 exit
}
function Restore {
 Closed
 $m=Get-Content "$backup\manifest.json" -Raw|ConvertFrom-Json
 foreach($n in $m.install){if(Test-Path "$game\$n"){Remove-Item "$game\$n" -Recurse -Force}}
 foreach($n in $m.saved){if(Test-Path "$backup\$n"){Move-Item "$backup\$n" "$game\$n" -Force}}
 Move-Item "$backup\manifest.json" "$backup\restored-manifest.json" -Force
 'RESTORED'
}
if($Action -eq 'Package'){
 if(Test-Path $stage){throw 'Staging exists; inspect it before rebuilding.'}
 New-Item -ItemType Directory $stage|Out-Null
 Copy-Item "$lab\opti\*" $stage -Recurse
 Move-Item "$stage\OptiScaler.dll" "$stage\dxgi.dll"
 Copy-Item "$lab\DLSS5-AMD-0.23\d3d12.dll" "$stage\ReShade64.dll"
 Copy-Item "$lab\DLSS5-AMD-0.23\dlss5-amd.addon64" $stage
 Copy-Item "$lab\DLSS5-AMD-0.23\DLSS5-AMD" $stage -Recurse
 foreach($n in 'ReShade-LICENSE.txt','MinHook-LICENSE.txt'){Copy-Item "$lab\DLSS5-AMD-0.23\$n" $stage}
 $ini=Get-Content "$stage\OptiScaler.ini" -Raw
 foreach($kv in @(@('Dx12Upscaler','fsr31'),@('LoadReshade','true'),@('Dxgi','false'),@('LogToFile','true'),@('LogLevel','2'),@('FGInput','nofg'),@('FGOutput','nofg'))){
  $pattern='(?m)^'+$kv[0]+'=.*$'
  if($ini -notmatch $pattern){throw "Missing ini key $($kv[0])"}
  $ini=[regex]::Replace($ini,$pattern,($kv[0]+'='+$kv[1]))
 }
 [IO.File]::WriteAllText("$stage\OptiScaler.ini",$ini)
 Add-Content "$stage\DLSS5-AMD\native-game-flags.txt" "`nDLSS5_UPSCALER=ffx"
 @'
LOCAL TEST ONLY: OptiScaler 0.9.4 + DLSS5-AMD 0.23.
Not yet validated as a working combination. Not a release.
dxgi.dll = OptiScaler; ReShade64.dll = ReShade; dlss5-amd.addon64 = HIP network.
Start Stellar Blade with FSR upscaling, frame generation OFF, output <=1920x1080.
Insert: OptiScaler menu. F6: DLSS5 network toggle.
Verify OptiScaler.log and DLSS5-AMD/logs; an FPS overlay alone does not prove OptiScaler routing.
Deploy/restore with Development/tools/optiscaler-stellarblade.ps1.
Official OptiScaler source: https://github.com/optiscaler/OptiScaler
'@ | Set-Content "$stage\README-TEST.txt" -Encoding UTF8
 Archive
 exit
}
if($Action -eq 'Restore'){Restore;exit}
if($Action -eq 'Install'){
 Closed
 if(Test-Path $backup){throw 'Backup directory already exists.'}
 if(!(Test-Path "$stage\SHA256SUMS-test.txt")){throw 'Package first.'}
 foreach($line in Get-Content "$stage\SHA256SUMS-test.txt"){
  if((Get-FileHash (Join-Path $stage $line.Substring(66))).Hash -ne $line.Substring(0,64)){throw 'Staged hash mismatch'}
 }
 $install=@(Get-ChildItem $stage|ForEach-Object{$_.Name})
 $save=@($install+@('d3d12.dll','ReShade.ini','ReShade.log','OptiScaler.log')+@(Get-ChildItem "$game\*.addon64"|ForEach-Object{$_.Name})|Sort-Object -Unique|Where-Object{Test-Path "$game\$_"})
 New-Item -ItemType Directory $backup|Out-Null
 [pscustomobject]@{install=$install;saved=$save}|ConvertTo-Json -Depth 3|Set-Content "$backup\manifest.json"
 foreach($n in $save){Move-Item "$game\$n" "$backup\$n"}
 try {
  Copy-Item "$stage\*" $game -Recurse
  foreach($line in Get-Content "$stage\SHA256SUMS-test.txt"){
   if((Get-FileHash (Join-Path $game $line.Substring(66))).Hash -ne $line.Substring(0,64)){throw 'Installed hash mismatch'}
  }
 }catch{Restore;throw}
 'INSTALLED; old active add-ons and assets backed up.'
}
Get-Process SB-Win64-Shipping -ErrorAction SilentlyContinue|Select-Object ProcessName,Id
Get-ChildItem "$game\*.addon64","$game\dxgi.dll","$game\ReShade64.dll" -ErrorAction SilentlyContinue|Select-Object Name,Length
if($Action -eq 'Status'){
 if(Test-Path "$game\OptiScaler.log"){
  'OPTISCALER ROUTING:'
  Select-String -Path "$game\OptiScaler.log" -Pattern 'Creating new ffx upscaler' -Context 4,35|Select-Object -First 1|ForEach-Object{$_.ToString()}
  Select-String -Path "$game\OptiScaler.log" -Pattern 'fallback|falling|failed|FFXFeature.*Init|FSR2Feature.*Init'|Where-Object{$_.Line -notmatch 'Streamline|nvngx_update'}|Select-Object -First 30|ForEach-Object{$_.Line}
  Select-String -Path "$game\OptiScaler.log" -Pattern 'CreateFeature|ffxCreateContext|CreateContext|FFX_Dx12|FSR version|Upscaler.*created|upscaler.*init'|Select-Object -Last 35|ForEach-Object{$_.Line}
 }
 foreach($n in 'OptiScaler.log','ReShade.log','DLSS5-AMD\logs\native-game-oneshot.txt','DLSS5-AMD\logs\native-submission-order.txt','DLSS5-AMD\logs\native-hip.txt'){
  if(Test-Path "$game\$n"){Write-Output "LOG: $n";Get-Content "$game\$n" -Tail 18}
 }
}
