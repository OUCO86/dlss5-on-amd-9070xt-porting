param([ValidateSet('stellar','cyberpunk','both')][string]$Game='both',[switch]$Restore)
# 0.30 candidate add-on (a569ed6f...): dual hook + ASYNC=auto + DLSS5_STRENGTH=auto (per-title table: Cyberpunk2077.exe -> 1,0).
# Installs the DLL and removes any explicit DLSS5_STRENGTH line from native-game-flags.txt so the table decides.
# -Restore puts back the backed-up DLL and flags file. Skips a game that is running.
$ErrorActionPreference='Stop'
$l='D:\DLSSNR-Lab\addon030-strength-20260924'
$games=@{
 stellar=@{p='SB-Win64-Shipping';g='C:\Program Files (x86)\Steam\steamapps\common\StellarBlade\SB\Binaries\Win64'}
 cyberpunk=@{p='Cyberpunk2077';g='C:\Program Files (x86)\Steam\steamapps\common\Cyberpunk 2077\bin\x64'}
}
$names=if($Game -eq 'both'){@('stellar','cyberpunk')}else{@($Game)}
foreach($n in $names){$x=$games[$n]
 if(Get-Process $x.p -ErrorAction SilentlyContinue){"$n running, skipped";continue}
 $dll="$($x.g)\dlss5-amd.addon64";$flags="$($x.g)\DLSS5-AMD\native-game-flags.txt";$b="$l\backup-$n"
 if($Restore){Copy-Item "$b\dlss5-amd.addon64" $dll -Force;Copy-Item "$b\native-game-flags.txt" $flags -Force;"$n RESTORED from $b";continue}
 New-Item -ItemType Directory -Force $b|Out-Null
 if(!(Test-Path "$b\dlss5-amd.addon64")){Copy-Item $dll "$b\dlss5-amd.addon64";Copy-Item $flags "$b\native-game-flags.txt"}
 Copy-Item "$l\dlss5-amd.addon64" $dll -Force
 $lines=@(Get-Content $flags)|Where-Object{$_ -notmatch '^DLSS5_STRENGTH='}
 [IO.File]::WriteAllLines($flags,$lines)
 "$n INSTALLED add-on $((Get-FileHash $dll).Hash.Substring(0,16).ToLower())... STRENGTH line removed (table decides); BACKUP=$b"
}
