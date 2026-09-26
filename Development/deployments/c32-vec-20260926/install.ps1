param([string]$RestoreBackup='',[ValidateSet('stellar','cyberpunk')][string]$Game='stellar')
# Replace c32-wave1.hsaco (gfx1200/gfx1201) with the CW_VEC_INPUT+CW_PREFIX_SPLIT build (bit-exact; 900 -0.8%, 1080 -0.9%).
# No flag or add-on change (the module loads under DLSS5_HIP_WAVE_OWNED=1). PREPARED, NOT EXECUTED (2026-09-26).
# Run from D:\DLSSNR-Lab\c32-vec-20260926 (this script + payload\) with the game closed. -RestoreBackup <dir> undoes it.
$ErrorActionPreference='Stop'
$g=if($Game -eq 'cyberpunk'){'C:\Program Files (x86)\Steam\steamapps\common\Cyberpunk 2077\bin\x64'}else{'C:\Program Files (x86)\Steam\steamapps\common\StellarBlade\SB\Binaries\Win64'}
$proc=if($Game -eq 'cyberpunk'){'Cyberpunk2077'}else{'SB-Win64-Shipping'}
$root=Split-Path -Parent $MyInvocation.MyCommand.Path;$hip="$g\DLSS5-AMD\native-game-tiled-assets\HIP"
$old=@{gfx1200='E2EDB93AF6B4650D1E7AA739BD79C6F07E94F6D0CED09D2072283E3EC3053D44';gfx1201='73A2DFDBB84967086B7F8E36C1776163EE8D584B1240764ECEDC276B330DE3D2'}
$new=@{gfx1200='128BB82C0EF8847F561A21975D0846E4B6859FC34AB464266BAAD65BC494D8C4';gfx1201='7AC34418CD3DD9FBCDF3E5D534CFEEE610AF21966DD84D05D7CAB308FF4330D1'}
if(Get-Process $proc -ErrorAction SilentlyContinue){throw "$Game running; no module replacement allowed"}
if($RestoreBackup){foreach($a in $old.Keys){Copy-Item "$RestoreBackup\$a\c32-wave1.hsaco" "$hip\$a\c32-wave1.hsaco" -Force;if((Get-FileHash "$hip\$a\c32-wave1.hsaco").Hash -ne $old[$a]){throw "restore verify $a"}};"RESTORED $RestoreBackup";exit}
foreach($a in $old.Keys){$t="$hip\$a\c32-wave1.hsaco";if((Get-FileHash $t).Hash -ne $old[$a]){throw "installed $a c32-wave1 is not the 0.31 module"};if((Get-FileHash "$root\payload\$a\c32-wave1.hsaco").Hash -ne $new[$a]){throw "payload hash $a"}}
$b="$root\backups\$Game-$(Get-Date -Format yyyyMMdd-HHmmss)"
foreach($a in $old.Keys){New-Item -ItemType Directory -Force "$b\$a"|Out-Null;Copy-Item "$hip\$a\c32-wave1.hsaco" "$b\$a\c32-wave1.hsaco"}
try{foreach($a in $old.Keys){Copy-Item "$root\payload\$a\c32-wave1.hsaco" "$hip\$a\c32-wave1.hsaco" -Force;if((Get-FileHash "$hip\$a\c32-wave1.hsaco").Hash -ne $new[$a]){throw "install verify $a"}}}
catch{foreach($a in $old.Keys){Copy-Item "$b\$a\c32-wave1.hsaco" "$hip\$a\c32-wave1.hsaco" -Force};throw}
"INSTALLED c32-wave1 (vec input + prefix split) gfx1200/gfx1201; BACKUP=$b"
