$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend';$d="$r\ffn-expand-prefetch"
$s="#define HIP_ISA_HALF 1`n#define HIP_PREPACKED_WEIGHTS 1`n#define HIP_FFN_HOIST_RES 2`n"+[IO.File]::ReadAllText("$d\multihead_fast_padded.hip")
[IO.File]::WriteAllText("$d\packed.hip",$s)
foreach($arch in 'gfx1200','gfx1201'){
 New-Item -ItemType Directory -Force "$d\$arch"|Out-Null
 & 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$d\$arch\multihead-fast-padded-wave-packed.hsaco" "$d\packed.hip" comgr $arch
 if($LASTEXITCODE){throw 'Compile failed'}
}
$m="$r\ffn-expand-prefetch-modules";New-Item -ItemType Directory -Force $m|Out-Null
Copy-Item "$r\post-head-shared-input-modules\*.hsaco" $m
Copy-Item "$d\gfx1201\*.hsaco" $m
