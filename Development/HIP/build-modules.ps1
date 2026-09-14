param(
    [Parameter(Mandatory=$true)][string]$Compiler,
    [Parameter(Mandatory=$true)][string]$OutputDir,
    [string]$SourceDir = $PSScriptRoot
)
$ErrorActionPreference = 'Stop'
$OutputDir = [IO.Path]::GetFullPath($OutputDir)
New-Item -ItemType Directory -Force $OutputDir | Out-Null
$utf8 = New-Object Text.UTF8Encoding($false)
$modules = @(
    @('c32_prefix_reference', @('c32_reference.hip', 'prefix_reference.hip')),
    @('multihead-reference', @('multihead_reference.hip')),
    @('deep_reference', @('deep_reference.hip')),
    @('boundary_reference', @('boundary_reference.hip')),
    @('c32_wmma', @('c32_wmma.hip')),
    @('multihead-wmma', @('multihead_wmma.hip')),
    @('deep_wmma', @('deep_wmma.hip')),
    @('wave-pointwise', @('c32_reference.hip', 'wave_pointwise.hip'))
)
foreach ($module in $modules) {
    $source = ''
    foreach ($part in $module[1]) {
        $source += [IO.File]::ReadAllText((Join-Path $SourceDir $part)) + "`n"
    }
    $sourcePath = Join-Path $OutputDir ($module[0] + '.generated.hip')
    [IO.File]::WriteAllText($sourcePath, $source, $utf8)
    & $Compiler (Join-Path $OutputDir ($module[0] + '.hsaco')) $sourcePath comgr
    if ($LASTEXITCODE -ne 0) { throw "COMGR failed: $($module[0])" }
}
