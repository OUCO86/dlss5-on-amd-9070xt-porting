$ErrorActionPreference='Stop'
$g='C:\Program Files (x86)\Steam\steamapps\common\RESIDENT EVIL requiem BIOHAZARD requiem'
if(Get-Process re9 -ErrorAction SilentlyContinue){throw 'Game is running; close before changing configuration'}
$b='D:\DLSSNR-Lab\re9-presr\backups\colour-'+(Get-Date -Format yyyyMMdd-HHmmss)
New-Item -ItemType Directory $b|Out-Null
foreach($relative in @('OptiScaler.ini','_storage_\OptiScaler.ini')){
 $p=Join-Path $g $relative
 $dest=Join-Path $b $relative
 New-Item -ItemType Directory (Split-Path $dest) -Force|Out-Null
 Copy-Item $p $dest
 $text=[IO.File]::ReadAllText($p)
 $section=[regex]::Match($text,'(?ms)^\[DlssNr\]\r?\n.*?(?=^\[|\z)')
 if(!$section.Success){throw "Missing DlssNr section in $p"}
 $new=$section.Value
 foreach($pair in @(@('Enabled','true'),@('TransferStrength','1.0'),@('ColourStrength','0.0'))){
  $pattern='(?m)^'+$pair[0]+'=[^\r\n]*'
  if([regex]::IsMatch($new,$pattern)){$new=[regex]::Replace($new,$pattern,($pair[0]+'='+$pair[1]))}
  else{$new+="`r`n"+$pair[0]+'='+$pair[1]+"`r`n"}
 }
 $text=$text.Substring(0,$section.Index)+$new+$text.Substring($section.Index+$section.Length)
 [IO.File]::WriteAllText($p,$text)
 $read=[IO.File]::ReadAllText($p)
 if($read -notmatch '(?m)^ColourStrength=0\.0\r?$' -or $read -notmatch '(?m)^TransferStrength=1\.0\r?$'){throw 'Config verification failed'}
 "UPDATED $relative : Enabled=true TransferStrength=1.0 ColourStrength=0.0"
}
"BACKUP $b"
