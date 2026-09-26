$ErrorActionPreference='Stop';$d=Split-Path -Parent $MyInvocation.MyCommand.Path;$r='D:\DLSSNR-Lab\hip-backend'
& "$r\check-idle.ps1"
$rows=@()
foreach($name in 'c32-wave1','c64-wave2'){
 $out="$d\recipe-check\$name"
 & "$d\source\build-modules.ps1" -SourceDir "$d\source" -OutputDir $out -Compiler 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' -Only $name -Targets gfx1201
 if($LASTEXITCODE){throw 'Recipe failed'}
 $actual=(Get-FileHash "$out\$name.hsaco").Hash;$expected=(Get-FileHash "$d\modules-gfx1201\$name.hsaco").Hash
 # COMGR includes a source-dependent compilation-unit symbol; compare all instructions and metadata after normalizing only that symbol.
 $left=([IO.File]::ReadAllText("$out\$name.hsaco.s")).Replace("`r`n","`n") -replace '__hip_cuid_[0-9a-fA-F]+','__hip_cuid_NORMALIZED'
 $right=([IO.File]::ReadAllText("$d\modules-gfx1201\$name.hsaco.s")).Replace("`r`n","`n") -replace '__hip_cuid_[0-9a-fA-F]+','__hip_cuid_NORMALIZED'
 if($left -cne $right){throw "Recipe instructions/metadata differ: $name"}
 $rows+=@{module=$name;recipe_sha256=$actual;incremental_sha256=$expected;normalized_assembly_equal=$true;normalization='__hip_cuid_<hex> only'}
}
[IO.File]::WriteAllText("$d\recipe-check.json",($rows|ConvertTo-Json),(New-Object Text.UTF8Encoding($false)))
