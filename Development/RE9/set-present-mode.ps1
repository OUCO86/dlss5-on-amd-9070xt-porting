param([ValidateRange(0,2)][int]$Mode=2)
$ErrorActionPreference='Stop'
$g='C:\Program Files (x86)\Steam\steamapps\common\RESIDENT EVIL requiem BIOHAZARD requiem'
$Mode.ToString()|Set-Content "$g\DLSS5-AMD\re9-present-mode.txt" -Encoding ASCII
"Mode $Mode (0 conversion, 1 HIP, 2 bypass)"
