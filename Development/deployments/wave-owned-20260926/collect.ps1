$ErrorActionPreference='Stop';$d=Split-Path -Parent $MyInvocation.MyCommand.Path;$root="$d\runtime-regression";$out="$d\runtime-evidence"
New-Item -ItemType Directory -Force $out | Out-Null
$cases=@()
foreach($dir in Get-ChildItem $root -Directory){
 if(!(Test-Path "$($dir.FullName)\rgb.csv")){continue}
 $dest="$out\$($dir.Name)";New-Item -ItemType Directory -Force $dest | Out-Null
 foreach($name in 'run.log','rgb.csv','flags.txt'){Copy-Item "$($dir.FullName)\$name" $dest}
 $frames=@(Get-ChildItem $dir.FullName -Filter '*frame-*.f16' | Sort-Object Name | ForEach-Object {@{name=$_.Name;sha256=(Get-FileHash $_.FullName).Hash}})
 $rows=@(Import-Csv "$($dir.FullName)\rgb.csv")
 $cases+=@{tag=$dir.Name;count=$rows.Count;frames=$frames;final_sha256=(Get-FileHash "$($dir.FullName)\rgb.f16").Hash}
}
[IO.File]::WriteAllText("$out\frame-hashes.json",($cases|ConvertTo-Json -Depth 6),(New-Object Text.UTF8Encoding($false)))
