$ErrorActionPreference='Stop'
$d=Split-Path -Parent $MyInvocation.MyCommand.Path
$root="$d\regression";$cases=@()
foreach($base in @(Get-ChildItem $root -Directory | Where-Object {$_.Name -like 'base-*' -or $_.Name -like '*-False'})){
 $name=if($base.Name -like 'base-*'){$base.Name -replace '^base-','candidate-'}else{$base.Name -replace '-False$','-True'}
 $candidate=Join-Path $root $name
 $files=@(Get-ChildItem $base.FullName -Filter '*frame-*.f16' | Sort-Object Name)
 if($files.Count -ne 12){throw "Expected 12 frames: $($base.Name)"}
 $frames=@()
 foreach($file in $files){
  $a=(Get-FileHash $file.FullName).Hash;$b=(Get-FileHash (Join-Path $candidate $file.Name)).Hash
  if($a -ne $b){throw "Mismatch: $($base.Name) $($file.Name)"}
  $frames+=@{file=$file.Name;sha256=$a}
 }
 $cases+=@{baseline=$base.Name;candidate=$name;frames=$frames}
}
if($cases.Count -ne 8){throw 'Expected eight regression cases'}
$manifest=@{cases=$cases;candidate_gfx1201=(Get-FileHash "$d\candidate-modules\c32_fused_ffn_attention-packed.hsaco").Hash;candidate_gfx1200=(Get-FileHash "$d\candidate-gfx1200\c32_fused_ffn_attention-packed.hsaco").Hash}
[IO.File]::WriteAllText("$d\validation.json",($manifest|ConvertTo-Json -Depth 6),(New-Object Text.UTF8Encoding($false)))
'PASS: eight cases, 96 candidate frames exactly match prod8'
