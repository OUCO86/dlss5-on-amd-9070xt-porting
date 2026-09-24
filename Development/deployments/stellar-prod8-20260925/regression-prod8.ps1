param([switch]$TimingOnly,[int]$TimingFrames=160,[switch]$ExtraControls,[int[]]$Heights=@(900,1080))
$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\network-fixed-shapes\regression-prod8";$a='D:\DLSSNR-Lab\Magpie-DLSS5-AMD-0.23\DLSS5-AMD'
function Idle {if(Get-Process LOP-Win64-Shipping,SB-Win64-Shipping,OnimushaWotS,re9,Magpie -ErrorAction SilentlyContinue){throw 'Game running'}}
Idle
function One($tag,$height,$seq,$candidate,$frames,$temporal=0,$extra=@()){
 Idle;$dir="$d\$tag";New-Item -ItemType Directory -Force $dir|Out-Null
 $flags=@(Get-Content "$a\native-game-flags.txt")+@('DLSS5_HIP_MH_FEATURE_BYTE=1','DLSS5_HIP_MH_PROJ_DIAG_FB=1','DLSS5_HIP_MH_BYTE_STREAM=1','DLSS5_HIP_DECODER_BYTE=1','DLSS5_HIP_VIT_BYTE_STREAM=0','DLSS5_HIP_MH_FFN_FRAG256=1','DLSS5_HIP_GRAPH=0','DLSS5_SHOW_FPS=0','DLSS5_PRE_UPSCALE=0',"DLSS5_NETWORK_HEIGHT=$height",'DLSS5_VIT_ADAPTIVE=0',"DLSS5_RESIDUAL_SEQUENCE=$seq","DLSS5_RESIDUAL_RGB=$(if($frames -eq 12){1}else{0})")
 if($candidate){$extra=@($extra)+@('DLSS5_HIP_PDL=1')}else{$extra=@($extra)+@('DLSS5_HIP_PDL=0')}
 [IO.File]::WriteAllLines("$dir\flags.txt",$flags+$extra)
 $m=if($candidate){"$r\network-fixed-shapes\prod8-modules"}else{"$r\network-fixed-shapes\prod2-modules"}
 $runner='benchmark_main_reuse_pdl.exe'
 & "$r\$runner" "$a\native-game-tiled-assets" "$dir\flags.txt" "$r\live-menu-before.f16" "$dir\rgb" $frames $temporal $m 0 $(if($frames -eq 12){0}else{1}) 0 0 > "$dir\run.log"
 if($LASTEXITCODE){throw 'Replay failed'};Idle
 $rows=@(Import-Csv "$dir\rgb.csv");if($rows.Count -ne $frames -or @($rows|Where-Object{$_.checked -eq '1' -and [int]$_.invalid -ne 0}).Count){throw 'Invalid frames'}
 $mean=($rows|Where-Object{[int]$_.frame -ge $(if($frames -eq 12){1}elseif($frames -ge 1000){200}else{32})}|Measure-Object wall_ms -Average).Average
 [pscustomobject]@{tag=$tag;mean_ms=$mean;sha=(Get-FileHash "$dir\rgb.f16").Hash}|ConvertTo-Json -Compress
}
if($ExtraControls){
 foreach($case in @(
  @{name='720-motion';height=720;seq=1;temporal=0;extra=@()},
  @{name='900-history';height=900;seq=5;temporal=1;extra=@()},
  @{name='900-float-in';height=900;seq=1;temporal=0;extra=@('DLSS5_HIP_MH_BYTE_STREAM=0')},
  @{name='900-float-feature';height=900;seq=1;temporal=0;extra=@('DLSS5_HIP_MH_BYTE_STREAM=0','DLSS5_HIP_MH_FEATURE_BYTE=0','DLSS5_HIP_MH_PROJ_DIAG_FB=0')}
 )){
  foreach($candidate in $false,$true){$tag="extra-$($case.name)-$candidate";One $tag $case.height $case.seq $candidate 12 $case.temporal $case.extra}
  $base="$d\extra-$($case.name)-False";$test="$d\extra-$($case.name)-True"
  $files=@(Get-ChildItem $base -Filter '*frame-*.f16');if($files.Count -ne 12){throw 'Missing RGB frames'}
  foreach($f in $files){if((Get-FileHash $f.FullName).Hash -ne (Get-FileHash "$test\$($f.Name)").Hash){throw 'Extra control output changed'}}
 }
 exit 0
}
foreach($h in $Heights){
 if(!$TimingOnly){foreach($seq in 0,1){One "base-$h-$seq" $h $seq $false 12;One "candidate-$h-$seq" $h $seq $true 12
  $files=@(Get-ChildItem "$d\base-$h-$seq" -Filter '*frame-*.f16');if($files.Count -ne 12){throw 'Missing RGB frames'}
  foreach($f in $files){if((Get-FileHash $f.FullName).Hash -ne (Get-FileHash "$d\candidate-$h-$seq\$($f.Name)").Hash){throw 'Output changed'}}
 }
 }
 foreach($slot in 0..3){One "$(if($TimingOnly){'repeat'}else{'time'})-$h-$slot" $h 0 ($slot -in 1,2) $TimingFrames}
}
