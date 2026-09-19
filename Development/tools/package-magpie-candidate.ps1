param([string]$Version='0.24.2',[string]$Base='D:\DLSSNR-Lab\Magpie-DLSS5-AMD-0.23',
 [string]$Addon='D:\DLSSNR-Lab\pre-upscale\native-idle-tracking.addon64',
 [string]$AddonSha='395DABFE20261832FAC8A43188EB69661BAA52EB140C8A99655D8B7F4E4AC75D',
 [string]$OutputDirectory='D:\給網友打包')
$ErrorActionPreference='Stop';$utf8=New-Object Text.UTF8Encoding($false)
$stage=Join-Path $OutputDirectory "Magpie-DLSS5-AMD-$Version"
if((Test-Path $stage) -or (Test-Path "$stage.zip")){throw 'Output already exists'}
if((Get-FileHash $Addon).Hash -ne $AddonSha){throw 'Candidate hash mismatch'}
# Validate the archived baseline before copying; never read a live Magpie installation.
foreach($line in [IO.File]::ReadAllLines("$Base\SHA256SUMS.txt")){
 if((Get-FileHash (Join-Path $Base $line.Substring(66))).Hash -ne $line.Substring(0,64)){throw 'Baseline checksum mismatch'}
}
New-Item -ItemType Directory -Force $OutputDirectory|Out-Null
Copy-Item $Base $stage -Recurse
Copy-Item $Addon "$stage\dlss5-amd.addon64" -Force
Copy-Item 'D:\DLSSNR-Lab\package-README-magpie-hip.txt' "$stage\README.txt" -Force
[IO.File]::WriteAllText("$stage\DLSS5-AMD-VERSION.txt","DLSS5-AMD $Version Magpie test (HIP gfx1201) addon sha256 $AddonSha`n",$utf8)
$flag="$stage\DLSS5-AMD\native-game-flags.txt"
$lines=@(Get-Content $flag|Where-Object{$_ -notmatch '^DLSS5_PRE_UPSCALE(_ASYNC|_DEBUG)?='})+@('DLSS5_PRE_UPSCALE=0')
[IO.File]::WriteAllLines($flag,$lines,$utf8)
$allowed=@('dlss5-amd.addon64','README.txt','DLSS5-AMD-VERSION.txt','DLSS5-AMD\native-game-flags.txt','SHA256SUMS.txt')
foreach($f in Get-ChildItem $stage -Recurse -File){
 $rel=$f.FullName.Substring($stage.Length+1)
 if($rel -notin $allowed -and (Get-FileHash $f.FullName).Hash -ne (Get-FileHash (Join-Path $Base $rel)).Hash){throw "Unexpected changed payload $rel"}
}
if(@(Get-ChildItem "$stage\DLSS5-AMD\native-game-tiled-assets\HIP\*.hsaco").Count -ne 24){throw 'Expected 24 HIP modules'}
if((Get-FileHash "$stage\dlss5-amd.addon64").Hash -ne $AddonSha){throw 'Staged addon mismatch'}
function Sums($stage){$lines=@(Get-ChildItem $stage -Recurse -File|Where-Object{$_.Name -ne 'SHA256SUMS.txt'}|Sort-Object FullName|ForEach-Object{(Get-FileHash $_.FullName).Hash.ToLowerInvariant()+'  '+$_.FullName.Substring($stage.Length+1).Replace('\','/')});[IO.File]::WriteAllLines("$stage\SHA256SUMS.txt",$lines,$utf8);$lines.Count}
function Zip($stage){New-Item -ItemType Directory -Force $OutputDirectory|Out-Null;$zip=Join-Path $OutputDirectory ((Split-Path $stage -Leaf)+'.zip');if(Test-Path $zip){Remove-Item $zip};Add-Type -AssemblyName System.IO.Compression.FileSystem;[IO.Compression.ZipFile]::CreateFromDirectory($stage,$zip,[IO.Compression.CompressionLevel]::Fastest,$true)
 $lines=[IO.File]::ReadAllLines("$stage\SHA256SUMS.txt");$archive=[IO.Compression.ZipFile]::OpenRead($zip);$n=0
 try{$prefix=(Split-Path $stage -Leaf)+'/';$entries=@{};foreach($e in $archive.Entries){$entries[$e.FullName.Replace('\','/')]=$e}
  foreach($line in $lines){$hash=$line.Substring(0,64);$name=$line.Substring(66);$e=$entries[$prefix+$name];if(!$e){throw "missing archive entry $name"};$s=$e.Open();$sha=[Security.Cryptography.SHA256]::Create();try{$actual=([BitConverter]::ToString($sha.ComputeHash($s))).Replace('-','').ToLowerInvariant()}finally{$s.Dispose();$sha.Dispose()};if($actual -ne $hash){throw "archive hash mismatch $name"};$n++}}finally{$archive.Dispose()}
 $zh=(Get-FileHash $zip).Hash.ToLowerInvariant();[IO.File]::WriteAllText("$zip.sha256",$zh+'  '+(Split-Path $zip -Leaf)+"`n",$utf8);"$(Split-Path $zip -Leaf) files=$n bytes=$((Get-Item $zip).Length) sha256=$zh"}

Sums $stage
Zip $stage
