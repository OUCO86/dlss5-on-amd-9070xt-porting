param([string]$Root='D:\DLSSNR-Lab\hip-backend',
 [string]$Module='c32_fused_ffn_attention.hsaco',
 [string]$Baseline='c32-base.hsaco',
 [string]$Candidate='c32-rtz.hsaco',
 [uint32]$Seed=0,
 [string]$Assets='D:\DLSSNR-Lab\network-720p\DLSS5-AMD\native-game-tiled-assets')
$ErrorActionPreference='Stop'
if(Get-Process SB-Win64-Shipping -ErrorAction SilentlyContinue){throw 'Close Stellar Blade before offline GPU timing.'}
$work=Join-Path $Root 'module-swap-test'
New-Item -ItemType Directory -Force $work | Out-Null
$modules=Join-Path $work 'modules'
New-Item -ItemType Directory -Force $modules | Out-Null
Copy-Item "$Root\repro-modules\*.hsaco" $modules -Force
$rows=@();$expected=$null
foreach($round in 0..3){
 $variant=@('base','candidate','candidate','base')[$round]
  $source=if($variant -eq 'base'){$Baseline}else{$Candidate}
 Copy-Item (Join-Path $Root $source) (Join-Path $modules $Module) -Force
 $output=Join-Path $work "$round-$variant.f32"
 $log=& "$Root\reference_network.exe" $Assets $modules "$Root\input900.rgba32f" "$Assets\noise.f32" $output --900 --wmma --wave --tiled --pooled --fused-c32 --fused-ffn --fused-mh --fast-mh --mh-wave --fast-deep --fast-prefix --skip-blocks 42,43,46 --packed-weights --seed $Seed --repeat 6 2>&1
 if($LASTEXITCODE -ne 0){throw ($log -join "
")}
 $log | Set-Content "$work\$round-$variant.log"
 $hash=(Get-FileHash $output).Hash
 if($null -eq $expected){$expected=$hash}elseif($hash -ne $expected){throw 'Full network output mismatch'}
 foreach($line in $log){if("$line" -match '^iteration=(\d+) wall_seconds=([\d.]+)'){
  $rows += [pscustomobject]@{round=$round;variant=$variant;iteration=[int]$Matches[1];ms=1000*[double]::Parse($Matches[2],[Globalization.CultureInfo]::InvariantCulture)}
 }}
 Write-Output "PASS round=$round variant=$variant hash=$hash"
}
$rows | Export-Csv "$work\timings.csv" -NoTypeInformation
foreach($variant in @('base','candidate')){
 $hot=@($rows | Where-Object {$_.variant -eq $variant -and $_.iteration -gt 0} | ForEach-Object {$_.ms} | Sort-Object)
 Write-Output "RESULT variant=$variant median_ms=$(($hot[4]+$hot[5])/2)"
}
