$ErrorActionPreference='Stop';$r='D:\DLSSNR-Lab\hip-backend'
$origin="$r\post-head-shared-input\gfx1201\c32_fused_ffn_attention-packed.hsaco"
$timed="$r\mh-empty-c256-modules\c32_fused_ffn_attention-packed.hsaco"
if((Get-FileHash $origin).Hash -ne (Get-FileHash $timed).Hash){throw 'C32 audit artifact mismatch'}
Get-FileHash $origin,$timed
