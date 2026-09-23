# Install / remove a 0.29 OptiScaler package in Wo Long 2 Alpha Demo (root EXE).
#   powershell -NoProfile -ExecutionPolicy Bypass -File install.ps1                      # regular OptiScaler package
#   powershell -NoProfile -ExecutionPolicy Bypass -File install.ps1 -Variant re9         # RE9 pre-SR host, without REFramework dinput8.dll
#   powershell -NoProfile -ExecutionPolicy Bypass -File install.ps1 [-Variant re9] -Uninstall
# Findings 2026-09-23: Wo Long 2 (Katana engine) loads amd_fidelityfx_upscaler_dx12.dll itself, so OptiScaler Detours its exports and
# dispatches through its trampolines; the regular addon only sees ffxDispatch with [Inputs] EnableFfxInputs=false. Even then the game
# records draws after the upscaler in the same command list, which the regular pre-upscale route refuses ("UNSAFE: draw/dispatch after
# deferred upscaler in same list"). The RE9 host splits the command list, so that route is the candidate.
param([switch]$Uninstall,[ValidateSet('regular','re9')][string]$Variant='regular')
$ErrorActionPreference = 'Stop'
$game = 'C:\Program Files (x86)\Steam\steamapps\common\Wo Long 2 Wings of Ember Alpha Demo'
$pkgName = if ($Variant -eq 're9') { 'OptiScaler-REFramework-DLSS5-AMD-0.29' } else { 'OptiScaler-DLSS5-AMD-0.29' }
$pkg = (Get-Item "D:\*\$pkgName" | Select-Object -First 1).FullName
if (-not (Test-Path "$game\WoLong2.exe")) { throw "game exe not found in $game" }
if (Get-Process WoLong2 -ErrorAction SilentlyContinue) { throw 'WoLong2.exe is running; close the game first' }

# package file list = SHA256SUMS.txt entries (relative paths) + the sums file itself; RE9 variant drops REFramework and the source archive
$list = Get-Content "$pkg\SHA256SUMS.txt" | ForEach-Object { ($_ -split '\s+', 2)[1].TrimStart('*') } | Where-Object { $_ }
$list += 'SHA256SUMS.txt'
if ($Variant -eq 're9') { $list = $list | Where-Object { $_ -ne 'dinput8.dll' -and $_ -notmatch '^sources[\\/]' } }
$backup = Join-Path $game '_dlss5_backup'

if ($Uninstall) {
  $n = 0
  foreach ($rel in $list) {
    $p = Join-Path $game $rel
    if (Test-Path $p) { Remove-Item -LiteralPath $p -Force; $n++ }
  }
  foreach ($d in @('DLSS5-AMD','D3D12_Optiscaler','Licenses','sources')) {
    $p = Join-Path $game $d
    if (Test-Path $p) { Remove-Item -LiteralPath $p -Recurse -Force }
  }
  Get-ChildItem $game -Filter 'OptiScaler*.log' | Remove-Item -Force
  Get-ChildItem $game -Filter '*.log' | Where-Object { $_.Name -match '^(ReShade|fakenvapi)' } | Remove-Item -Force
  if (Test-Path $backup) {
    Get-ChildItem $backup -File | Where-Object { $_.Name -notmatch '\.029$' } | ForEach-Object { Move-Item -LiteralPath $_.FullName -Destination (Join-Path $game $_.Name) -Force }
    Remove-Item -LiteralPath $backup -Recurse -Force
    'restored game-shipped files from _dlss5_backup'
  }
  "removed $n package files + dirs"
  exit 0
}

# game-shipped files that the package overwrites (libxess*.dll, libxell.dll) go to a backup dir
$clash = $list | Where-Object { Test-Path (Join-Path $game $_) }
if ($clash) {
  if (Test-Path $backup) { throw "$backup already exists; uninstall first" }
  New-Item -ItemType Directory -Path $backup | Out-Null
  foreach ($rel in $clash) { Move-Item -LiteralPath (Join-Path $game $rel) -Destination (Join-Path $backup $rel) }
  "backed up: $($clash -join ', ')"
}

$n = 0
foreach ($rel in $list) {
  $src = Join-Path $pkg $rel; $dst = Join-Path $game $rel
  $dir = Split-Path $dst
  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
  Copy-Item -LiteralPath $src -Destination $dst -Force
  $n++
}
"copied $n files from $pkg (variant $Variant)"
Get-Content "$game\DLSS5-AMD-VERSION.txt"
"flags: " + ((Get-Content "$game\DLSS5-AMD\native-game-flags.txt" | Where-Object { $_ -match 'FIT_LARGE|NETWORK_HEIGHT' }) -join ' ')
