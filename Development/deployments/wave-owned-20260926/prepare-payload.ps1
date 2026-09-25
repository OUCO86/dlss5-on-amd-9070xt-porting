$ErrorActionPreference='Stop';$d=Split-Path -Parent $MyInvocation.MyCommand.Path
$items=@();$baseline=@()
foreach($arch in 'gfx1200','gfx1201'){
 foreach($f in Get-ChildItem "$d\modules-$arch\*.hsaco"){
  $row=@{source=$f.FullName;target="DLSS5-AMD/native-game-tiled-assets/HIP/$arch/$($f.Name)";sha256=(Get-FileHash $f.FullName).Hash}
  if($f.BaseName -in 'c32-wave1','c64-wave2'){$items+=$row}else{$baseline+=$row}
 }
}
# gfx1200 lab baseline is incremental (five changed modules); gfx1201 contains all 24 legacy modules.
if($items.Count -ne 4 -or @($baseline|Where-Object {$_.target -match '/gfx1201/'}).Count -ne 24 -or @($baseline|Where-Object {$_.target -match '/gfx1200/'}).Count -lt 5){throw 'Unexpected module inventory'}
$items+=@{source="$d\dlss5-amd.addon64";target='dlss5-amd.addon64';sha256=(Get-FileHash "$d\dlss5-amd.addon64").Hash}
[IO.File]::WriteAllText("$d\payload.json",($items|ConvertTo-Json -Depth 4),(New-Object Text.UTF8Encoding($false)))
[IO.File]::WriteAllText("$d\baseline.json",($baseline|ConvertTo-Json -Depth 4),(New-Object Text.UTF8Encoding($false)))
