param([int[]]$Heights=@(900,1080),[int]$Frames=400)
$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\clock-ledger";$a='D:\DLSSNR-Lab\Magpie-DLSS5-AMD-0.23\DLSS5-AMD'
& "$r\check-idle.ps1"
New-Item -ItemType Directory -Force $d|Out-Null
$configs=@(@{n='base';p='';c=1},@{n='c32x8';p='c32_';c=8},@{n='c64-256x8';p='mh_ffn_fused_c';c=8},@{n='attnx8';p='c';c=0},@{n='c512x8';p='split_';c=8},@{n='vitx8';p='vit_';c=8},@{n='base2';p='';c=1})
foreach($height in $Heights){
 foreach($cfg in $configs){
  $folder="$d\$height-$($cfg.n)";New-Item -ItemType Directory -Force $folder|Out-Null
  $base=@(Get-Content "$r\network-timeline\$height\flags.txt"|Where-Object{$_ -notmatch '^DLSS5_HIP_DUP_PREFIX=|^DLSS5_HIP_DUP_COUNT='})
  if($cfg.n -eq 'attnx8'){$lines=$base+@('DLSS5_HIP_DUP_PREFIX=c256_attention','DLSS5_HIP_DUP_COUNT=8')}elseif($cfg.p){$lines=$base+@("DLSS5_HIP_DUP_PREFIX=$($cfg.p)","DLSS5_HIP_DUP_COUNT=$($cfg.c)")}else{$lines=$base}
  [IO.File]::WriteAllLines("$folder\flags.txt",$lines)
  $p=Start-Process "$r\clock_observe_telemetry.exe" -ArgumentList '200' -PassThru -NoNewWindow -RedirectStandardOutput "$folder\telemetry.log" -RedirectStandardError "$folder\telemetry.err"
  Start-Sleep -Milliseconds 600
  try{
   $t0=[Environment]::TickCount64
   & "$r\benchmark_clock_observe.exe" "$a\native-game-tiled-assets" "$folder\flags.txt" "$r\live-menu-before.f16" "$folder\rgb" $Frames 0 "$r\network-fixed-shapes\prod6-modules" 0 1 0 0 > "$folder\run.log" 2> "$folder\run.err"
   $t1=[Environment]::TickCount64
   "start=$t0 end=$t1 exit=$LASTEXITCODE" | Set-Content "$folder\window.txt"
   if($LASTEXITCODE){throw "benchmark failed $height $($cfg.n)"}
  }finally{if(!$p.HasExited){Stop-Process -Id $p.Id -Force}}
  "$height $($cfg.n) done"
 }
}
