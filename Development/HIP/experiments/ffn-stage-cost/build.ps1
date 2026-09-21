$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\ffn-stage-cost"
foreach($stage in 'expand','contract','project','qkv'){
 $m="$d\$stage";New-Item -ItemType Directory -Force $m|Out-Null
 Copy-Item "$r\post-head-shared-input-modules\*.hsaco" $m
 & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$m\multihead-fast-padded-wave-packed.hsaco" "$d\$stage.hip" comgr gfx1201
 if($LASTEXITCODE){throw "Compile failed $stage"}
}
