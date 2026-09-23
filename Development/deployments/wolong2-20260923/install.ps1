# Install / remove the 0.29 regular OptiScaler package in Wo Long 2 Alpha Demo (root EXE).
#   powershell -NoProfile -ExecutionPolicy Bypass -File install.ps1             # install
#   powershell -NoProfile -ExecutionPolicy Bypass -File install.ps1 -Uninstall  # remove package files only
param([switch]$Uninstall)
$ErrorActionPreference = 'Stop'
$game = 'C:\Program Files (x86)\Steam\steamapps\common\Wo Long 2 Wings of Ember Alpha Demo'
$pkg = (Get-Item 'D:\*\OptiScaler-DLSS5-AMD-0.29' | Select-Object -First 1).FullName
if (-not (Test-Path "$game\WoLong2.exe")) { throw "game exe not found in $game" }
if (Get-Process WoLong2 -ErrorAction SilentlyContinue) { throw 'WoLong2.exe is running; close the game first' }

# package file list = SHA256SUMS.txt entries (relative paths) + the sums file itself
$list = Get-Content "$pkg\SHA256SUMS.txt" | ForEach-Object { ($_ -split '\s+', 2)[1].TrimStart('*') } | Where-Object { $_ }
$list += 'SHA256SUMS.txt'

if ($Uninstall) {
  $n = 0
  foreach ($rel in $list) {
    $p = Join-Path $game $rel
    if (Test-Path $p) { Remove-Item -LiteralPath $p -Force; $n++ }
  }
  foreach ($d in @('DLSS5-AMD','D3D12_Optiscaler','Licenses')) {
    $p = Join-Path $game $d
    if (Test-Path $p) { Remove-Item -LiteralPath $p -Recurse -Force }
  }
  Get-ChildItem $game -Filter 'OptiScaler*.log' | Remove-Item -Force
  $backup = Join-Path $game '_dlss5_backup'
  if (Test-Path $backup) {
    Get-ChildItem $backup -File | ForEach-Object { Move-Item -LiteralPath $_.FullName -Destination (Join-Path $game $_.Name) -Force }
    Remove-Item -LiteralPath $backup -Recurse -Force
    'restored game-shipped files from _dlss5_backup'
  }
  "removed $n package files + dirs"
  exit 0
}

# game-shipped files that the package overwrites (libxess*.dll, libxell.dll) go to a backup dir
$backup = Join-Path $game '_dlss5_backup'
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
"copied $n files from $pkg"
Get-Content "$game\DLSS5-AMD-VERSION.txt"
"flags: " + (Get-Content "$game\DLSS5-AMD\native-game-flags.txt" | Where-Object { $_ -match 'FIT_LARGE|NETWORK_HEIGHT' }) -join ' '
