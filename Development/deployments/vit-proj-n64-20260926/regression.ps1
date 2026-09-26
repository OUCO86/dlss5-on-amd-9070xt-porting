# NativeGameFrame regression for DLSS5_HIP_VIT_PROJ_N64 on top of the installed production (both sides WAVE_OWNED=1, PDL=1, C512_M32=1).
param([switch]$CorrectnessOnly,[switch]$TimingOnly,[int]$TimingFrames=1000,[switch]$ExtraControls,[int[]]$Heights=@(900,1080))
$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$root=Split-Path -Parent $MyInvocation.MyCommand.Path;$d="$root\runtime-regression";$a='D:\DLSSNR-Lab\Magpie-DLSS5-AMD-0.23\DLSS5-AMD'
function Idle { & "$r\check-idle.ps1" }
Idle
function One($tag,$height,$seq,$candidate,$frames,$temporal=0,$extra=@(),$expectedActive=-1){
 Idle;$dir="$d\$tag";New-Item -ItemType Directory -Force $dir|Out-Null
 $flags=@(Get-Content "$a\native-game-flags.txt")+@('DLSS5_HIP_MH_FEATURE_BYTE=1','DLSS5_HIP_MH_PROJ_DIAG_FB=1','DLSS5_HIP_MH_BYTE_STREAM=1','DLSS5_HIP_DECODER_BYTE=1','DLSS5_HIP_VIT_BYTE_STREAM=0','DLSS5_HIP_MH_FFN_FRAG256=1','DLSS5_HIP_GRAPH=0','DLSS5_SHOW_FPS=0','DLSS5_PRE_UPSCALE=0',"DLSS5_NETWORK_HEIGHT=$height",'DLSS5_VIT_ADAPTIVE=0',"DLSS5_RESIDUAL_SEQUENCE=$seq","DLSS5_RESIDUAL_RGB=$(if($frames -eq 12){1}else{0})")
 $extra=@($extra)+@('DLSS5_HIP_PDL=1','DLSS5_HIP_WAVE_OWNED=1','DLSS5_HIP_C512_M32=1',"DLSS5_HIP_VIT_PROJ_N64=$(if($candidate){1}else{0})")
 [IO.File]::WriteAllLines("$dir\flags.txt",$flags+$extra)
 $runner=if($frames -eq 12){"$root\benchmark-trace.exe"}else{"$root\benchmark.exe"}
 & $runner "$a\native-game-tiled-assets" "$dir\flags.txt" "$r\live-menu-before.f16" "$dir\rgb" $frames $temporal "$root\modules-gfx1201" 0 $(if($frames -eq 12){0}else{1}) 0 0 > "$dir\run.log"
 if($LASTEXITCODE){throw "Replay failed $tag"};Idle
 if($frames -eq 12){
  $active=if($expectedActive -ge 0){[bool]$expectedActive}else{[bool]$candidate}
  $counts=Select-String -Path "$dir\run.log" -Pattern 'VIT_PROJ_N64_RUNTIME calls=(\d+) replaced=(\d+) enabled=(\d+)'
  if(!$counts){throw 'Missing ViT projection counters'}
  foreach($hit in $counts){$m=$hit.Matches[0];$calls=[int]$m.Groups[1].Value;$replaced=[int]$m.Groups[2].Value;if(($active -and ($calls -lt 8*$frames -or $calls%8 -ne 0 -or $replaced -ne $calls)) -or (!$active -and ($calls -eq 0 -or $replaced -ne 0))){throw "ViT projection count mismatch $tag calls=$calls replaced=$replaced"}}
 }
 $rows=@(Import-Csv "$dir\rgb.csv");if($rows.Count -ne $frames -or @($rows|Where-Object{$_.checked -eq '1' -and [int]$_.invalid -ne 0}).Count){throw 'Invalid frames'}
 $mean=($rows|Where-Object{[int]$_.frame -ge $(if($frames -eq 12){1}elseif($frames -ge 1000){200}else{32})}|Measure-Object wall_ms -Average).Average
 [pscustomobject]@{tag=$tag;mean_ms=$mean;sha=(Get-FileHash "$dir\rgb.f16").Hash}|ConvertTo-Json -Compress
}
function Same($b,$t){$files=@(Get-ChildItem "$d\$b" -Filter '*frame-*.f16');if($files.Count -ne 12){throw 'Missing RGB frames'};foreach($f in $files){if((Get-FileHash $f.FullName).Hash -ne (Get-FileHash "$d\$t\$($f.Name)").Hash){throw "Output changed $t"}};"SAME $b $t"}
if($ExtraControls){
 foreach($case in @(
  @{name='720-motion';height=720;seq=1;temporal=0;extra=@();active=-1},
  @{name='900-history';height=900;seq=5;temporal=1;extra=@();active=-1},
  @{name='1080-history';height=1080;seq=5;temporal=1;extra=@();active=-1},
  @{name='900-proj-nofrag';height=900;seq=1;temporal=0;extra=@('DLSS5_HIP_VIT_PROJ_FRAG=0');active=0}
 )){
  foreach($candidate in $false,$true){One "extra-$($case.name)-$candidate" $case.height $case.seq $candidate 12 $case.temporal $case.extra $case.active}
  Same "extra-$($case.name)-False" "extra-$($case.name)-True"
 }
 exit 0
}
foreach($h in $Heights){
 if(!$TimingOnly){foreach($seq in 0,1){One "base-$h-$seq" $h $seq $false 12;One "candidate-$h-$seq" $h $seq $true 12;Same "base-$h-$seq" "candidate-$h-$seq"}}
 if(!$CorrectnessOnly){foreach($slot in 0..3){One "time-$h-$slot" $h 0 ($slot -in 1,2) $TimingFrames}}
}
