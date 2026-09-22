$ErrorActionPreference='Stop'
$out='D:\給網友打包'
foreach($name in @('Magpie-DLSS5-AMD-0.28','OptiScaler-DLSS5-AMD-0.28','OptiScaler-REFramework-DLSS5-AMD-0.28')){
 $d=Join-Path $out $name
 $zh=[IO.File]::ReadAllText("$d\README.txt")
 if(!$zh.Contains('完整') -or !$zh.Contains('0.28')){throw "Chinese README invalid $name"}
 if(!(Test-Path "$d\README.en.txt")){throw 'English README missing'}
 foreach($arch in @('gfx1200','gfx1201')){if(@(Get-ChildItem "$d\DLSS5-AMD\native-game-tiled-assets\HIP\$arch\*.hsaco").Count -ne 24){throw 'Modules missing'}}
 if($name -like '*REFramework*'){
  $ini=[IO.File]::ReadAllText("$d\OptiScaler.ini")
  foreach($line in @('NrBackend=lmxxf','RunBeforeSR=true','TransferStrength=1.0','ColourStrength=1.0','LmxxfDiagnostic=off','LoadReshade=false')){if(!$ini.Contains($line)){throw "Missing RE9 setting $line"}}
  foreach($f in @('re9-present.addon64','dlss5-amd.addon64','DLSS5-AMD\native-game-flags.txt','config.ini')){if(Test-Path "$d\$f"){throw "Stale/personal file $f"}}
  if(!(Test-Path "$d\sources\re9-presr-source.tar.gz")){throw 'Corresponding source missing'}
 }else{
  $flags=[IO.File]::ReadAllText("$d\DLSS5-AMD\native-game-flags.txt")
  if($flags -notmatch '(?m)^DLSS5_VIT_ADAPTIVE=0\r?$'){throw 'Unexpected adaptive default'}
  if($flags -match '[CD]:\\'){throw 'Machine-specific default path'}
 }
 "CONFIG/README/MODULES OK $name"
}
