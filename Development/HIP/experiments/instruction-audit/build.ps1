$ErrorActionPreference='Stop';$d='D:\DLSSNR-Lab\hip-backend\instruction-audit'
$s="#define HIP_ISA_HALF 1`n#define HIP_PREPACKED_WEIGHTS 1`n#define HIP_FFN_HOIST_RES 2`n"+[IO.File]::ReadAllText("$d\multihead_fast_padded.hip")
[IO.File]::WriteAllText("$d\packed.hip",$s)
& 'D:\DLSSNR-Lab\dual-arch-src\rtc_compile.exe' "$d\multihead.hsaco" "$d\packed.hip" comgr gfx1201
if($LASTEXITCODE){throw 'Compile failed'}
