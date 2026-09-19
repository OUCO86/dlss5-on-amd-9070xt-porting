param([string]$Candidate='r960',[string]$Runner='benchmark_r960.exe',[string]$Reference='reference_g960.exe',[string]$Modules='ffnh2-modules',[string]$ExpectedFull='383FA5BCF544860F40D55E15E390E4154EDE54E784FE07366FB0445CCD93BFC3',[string]$ExpectedReset='698E1A39AFDF6BA47F53AD1BE559837076FF291E72ADD743C5BF7999AD2DC9C1',[string]$ExpectedHistory='78AF52D3FEA5068EBFA28E00047437011B0DED73578C0A2BC206F658CF470998',[string]$Assets='D:\DLSSNR-Lab\network-720p\DLSS5-AMD\native-game-tiled-assets',[string[]]$ExtraFlags=@(),[string[]]$ReferenceArgs=@())
# The three bit-exact checks on the shipped 900 tier (1600x900 padded to 960 rows, 0.22+): 40-frame HDR, 24-frame reset-every-8, seed-123 history via the
# reference chain (--960, input960.rgba32f). Goldens recorded 2026-09-17 21:05 (ffnh2-modules, native-r960 build) and reproduced; pass '' to record new ones.
$ErrorActionPreference='Stop'
$r='D:\DLSSNR-Lab\hip-backend'
$a=$Assets
if(Get-Process SB-Win64-Shipping -ErrorAction SilentlyContinue){throw 'Game running'}
@(Get-Content "$r\vitcf-on-flags.txt" | Where-Object {$_ -notmatch '^DLSS5_NETWORK_HEIGHT='})+@('DLSS5_NETWORK_HEIGHT=900')+$ExtraFlags | Set-Content "$r\flags960.txt"
& "$r\validate-hdr.ps1" -Assets $Assets -Runner $Runner -Modules $Modules -Name "$Candidate-full" -Flags flags960.txt -ExpectedHash $ExpectedFull
& "$r\validate-hdr.ps1" -Assets $Assets -Runner $Runner -Modules $Modules -Name "$Candidate-reset" -Flags flags960.txt -Frames 24 -ResetEvery 8 -ExpectedHash $ExpectedReset
$ref=@("$a","$r\$Modules","$r\input960.rgba32f","$a\noise.f32","$r\$Candidate-history.f32",'--960','--wmma','--wave','--tiled','--pooled','--fused-c32','--fused-ffn','--fused-mh','--fast-mh','--mh-wave','--fast-deep','--fast-prefix','--skip-blocks','42,43,46','--packed-weights','--packed-c32','--fp8-normalized','--fp8-ffn','--fp8-av','--fp8-deep','--fp8-middle','--half-c32','--crop-c32','--fused-qkv-norm','--fused-mh-ffn','--tiled-mh-ffn-large','--mapped-c32','--vit-blocked','--vit-contract-blocked','--vit-weight-mask','1','--vit-pack-input','--elide-identity-shift','--raw-chain','--pre-main8','--post-merge-fold','--fused-ffn-project','--split-ffn-fused','--split-mix-blocked','--split-project-blocked','--vit-qkv-blocked','--mh-project-crop','--mh-input-mapped','--prefix-fused','--direct-prefix-input','--grouped-mh-contract','--ffn-qkv','--ffn-qkv-max-c','256','--vit-qkv-fused','--vit-attn-fused','--vit-qkv-fp8','--vit-expand-frag','--split-mix-h16w','--pool-project-h16w','--decoder-h16w','--c512-qkv-frag','--c512-proj-frag','--c512-proj-tiles','--mh-proj-diag','--post-head-fused','--c32-finish-fused','--down-crop-fused','--pool32-h16w','--pool-project-group','--vit-proj-frag','--vit-qkv-frag','--vit-contract-frag','--prefix-inline')
$ref+=@('--seed','123','--history',"$r\input960.rgba32f",'--repeat','2')
& "$r\$Reference" @ref @ReferenceArgs > "$r\$Candidate-history.log"
if($LASTEXITCODE){throw 'history reference failed'}
if(Get-Process SB-Win64-Shipping -ErrorAction SilentlyContinue){throw 'Game started; discard timings'}
$h=(Get-FileHash "$r\$Candidate-history.f32").Hash
if($ExpectedHistory -and $h -ne $ExpectedHistory){throw "history output mismatch $h"}
Write-Output "history seed123 hash=$h"
Get-Content "$r\$Candidate-history.log" | Select-String 'reference complete'
