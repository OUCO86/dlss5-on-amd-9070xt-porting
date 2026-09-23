param([int[]]$Heights=@(1080),[int]$Frames=400)
# FFN-dominated frame (mh_ffn_fused_c dup x8) with the ffn_fused tail ablations: which part of the FFN kernel burns the power.
$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\clock-ledger-ffn";$a='D:\DLSSNR-Lab\Magpie-DLSS5-AMD-0.23\DLSS5-AMD'
& "$r\check-idle.ps1"
New-Item -ItemType Directory -Force $d|Out-Null
# module sets: prod6 everything, mh_fast from the ablation build (prod5-era kernel: mh5 = unablated, pair1..3 ablated)
foreach($set in 'mh5'){
 $m="$d\modules-$set";New-Item -ItemType Directory -Force $m|Out-Null
 Copy-Item "$r\network-fixed-shapes\prod6-modules\*.hsaco" $m -Force
 $src=if($set -eq 'mh5'){"$r\mhfast-tail-ablate\modules\multihead-fast-padded-wave-packed.hsaco"}else{"$r\mhfast-tail-ablate\modules\$set\multihead-fast-padded-wave-packed.hsaco"}
 Copy-Item $src "$m\multihead-fast-padded-wave-packed.hsaco" -Force
}
$order=@('p6','mh5','pair4','pair5','pair6','p6b','mh5b')
foreach($height in $Heights){
 $base=@(Get-Content "$r\network-timeline\$height\flags.txt"|Where-Object{$_ -notmatch '^DLSS5_HIP_DUP_PREFIX=|^DLSS5_HIP_DUP_COUNT='})
 foreach($set in $order){
  $ms=$set -replace 'b$','';$folder="$d\r2-$height-$set";New-Item -ItemType Directory -Force $folder|Out-Null
  [IO.File]::WriteAllLines("$folder\flags.txt",$base+@('DLSS5_HIP_DUP_PREFIX=mh_ffn_fused_c','DLSS5_HIP_DUP_COUNT=8'))
  $p=Start-Process "$r\clock_observe_telemetry.exe" -ArgumentList '200' -PassThru -NoNewWindow -RedirectStandardOutput "$folder\telemetry.log" -RedirectStandardError "$folder\telemetry.err"
  Start-Sleep -Milliseconds 600
  try{
   & "$r\benchmark_clock_observe.exe" "$a\native-game-tiled-assets" "$folder\flags.txt" "$r\live-menu-before.f16" "$folder\rgb" $Frames 0 "$d\modules-$ms" 0 1 0 0 > "$folder\run.log" 2> "$folder\run.err"
   "exit=$LASTEXITCODE" | Set-Content "$folder\window.txt"
  }finally{if(!$p.HasExited){Stop-Process -Id $p.Id -Force}}
  "$height $set done exit=$LASTEXITCODE"
 }
}
