param([Parameter(Mandatory)][ValidateSet('off','on','status')][string]$Do,[string[]]$Files=@())
# Bisect helper: -Do off renames the listed files (relative to Content) to <name>.off, -Do on puts them back, status lists
# every .off in the folder. Refuses while the game runs.
$ErrorActionPreference='Stop'
$g='C:\XboxGames\Forza Horizon 6\Content'
if(Get-Process forzahorizon6 -ErrorAction SilentlyContinue){throw 'Forza running'}
if($Do -eq 'status'){Get-ChildItem $g -Recurse -Filter *.off | ForEach-Object{$_.FullName.Substring($g.Length+1)};exit}
foreach($f in $Files){$p=Join-Path $g $f
 if($Do -eq 'off'){if(Test-Path $p){Rename-Item $p "$p.off";"OFF $f"}else{"MISSING $f"}}
 else{if(Test-Path "$p.off"){Rename-Item "$p.off" $p;"ON $f"}else{"NO .off for $f"}}}
