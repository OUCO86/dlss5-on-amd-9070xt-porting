param([switch]$Restore)
$ErrorActionPreference='Stop'
$game='C:\Program Files (x86)\Steam\steamapps\common\StellarBlade\SB\Binaries\Win64'
$root=Join-Path $game 'DLSS5-AMD'
$lab='D:\DLSSNR-Lab\hip-backend'
$backup=Join-Path $lab 'stellarblade-hip\before-fp8-edges'
$candidate=Join-Path $lab 'stellarblade-hip\native-fp8-edges.addon64'
$modules=Join-Path $lab 'edge-modules'
$target=Join-Path $game 'native-submission-order.addon64'
$expected='68C8BA0CA6293660BDAB99A66C6EAC71576133846DFCEF0C700BB8818DECD107'
function Closed {if(Get-Process SB-Win64-Shipping -ErrorAction SilentlyContinue){throw 'Close Stellar Blade before replacing DLL/modules.'}}
function RestoreBackup {
 Closed
 $record=Get-Content "$backup\manifest.json" -Raw|ConvertFrom-Json
 if((Get-FileHash "$backup\native-submission-order.addon64").Hash -ne $record.dll){throw 'Backup DLL hash mismatch'}
 foreach($m in $record.modules){if((Get-FileHash "$backup\HIP\$($m.name)").Hash -ne $m.sha256){throw 'Backup module hash mismatch'}}
 Copy-Item "$backup\native-submission-order.addon64" $target -Force
 Copy-Item "$backup\HIP\*" "$root\HIP" -Force
 Copy-Item "$backup\native-game-flags.txt" "$root\native-game-flags.txt" -Force
 Write-Output 'Restored previous HIP DLL/modules/configuration.'
}
Closed
if($Restore){RestoreBackup;exit}
if(Test-Path $backup){throw 'Backup exists; inspect before repeating deployment'}
if((Get-FileHash $candidate).Hash -ne $expected){throw 'Candidate DLL mismatch'}
$files=@(Get-ChildItem $modules -Filter '*.hsaco')
if($files.Count -ne 24){throw 'Expected 24 modules'}
$manifest=@($files|ForEach-Object{[pscustomobject]@{name=$_.Name;sha256=(Get-FileHash $_.FullName).Hash}})
if(!(Test-Path "$root\HIP-CANDIDATE.txt")){throw 'Existing HIP install not recognized'}
New-Item -ItemType Directory $backup|Out-Null
Copy-Item $target "$backup\native-submission-order.addon64"
Copy-Item "$root\HIP" "$backup\HIP" -Recurse
Copy-Item "$root\native-game-flags.txt" "$backup\native-game-flags.txt"
$old=@(Get-ChildItem "$backup\HIP" -Filter '*.hsaco'|ForEach-Object{[pscustomobject]@{name=$_.Name;sha256=(Get-FileHash $_.FullName).Hash}})
[pscustomobject]@{dll=(Get-FileHash $target).Hash;modules=$old}|ConvertTo-Json -Depth 4|Set-Content "$backup\manifest.json"
try {
 Closed
 foreach($m in $manifest){Copy-Item "$modules\$($m.name)" "$root\HIP\$($m.name)" -Force}
 Copy-Item $candidate $target -Force
 foreach($m in $manifest){if((Get-FileHash "$root\HIP\$($m.name)").Hash -ne $m.sha256){throw 'Installed module mismatch'}}
 if((Get-FileHash $target).Hash -ne $expected){throw 'Installed DLL mismatch'}
 $utf8=New-Object Text.UTF8Encoding($false)
 $flags=@(Get-Content "$root\native-game-flags.txt"|Where-Object{$_ -notmatch '^DLSS5_TEST_ASYNC_SUBMIT='})
 $flags+='DLSS5_TEST_ASYNC_SUBMIT=0'
 [IO.File]::WriteAllText("$root\native-game-flags.txt",($flags -join "`n")+"`n",$utf8)
 foreach($name in @('continuous-every-frame.txt','temporal-history.txt')){[IO.File]::WriteAllText("$root\$name","1`n",$utf8)}
 $manifest|ConvertTo-Json -Depth 3|Set-Content "$root\HIP\deployment-modules.json"
 [IO.File]::WriteAllText("$root\HIP-CANDIDATE.txt","HIP7 fast900P packed C32 / FP8 normalized + FFN + AV`nDLL SHA256=$expected`nSynchronous submissions`n",$utf8)
 Write-Output "INSTALLED_SHA=$expected MODULES=$($files.Count) BACKUP=$backup"
}catch{RestoreBackup;throw}
