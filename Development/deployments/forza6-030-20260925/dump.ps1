param([string]$Name='forzahorizon6',[string]$Out='D:\DLSSNR-Lab\forza6-030-20260925\hang.dmp')
# Minidump (threads + stacks + module list, no full memory) of a hung process, via dbghelp!MiniDumpWriteDump. No external tools.
$ErrorActionPreference='Stop'
$p=Get-Process $Name -ErrorAction SilentlyContinue|Select-Object -First 1
if(-not $p){throw "$Name not running"}
Add-Type -Name MD -Namespace W -MemberDefinition @'
[DllImport("dbghelp.dll",SetLastError=true)]
public static extern bool MiniDumpWriteDump(IntPtr hProcess,uint pid,IntPtr hFile,int type,IntPtr a,IntPtr b,IntPtr c);
'@
$fs=New-Object IO.FileStream($Out,[IO.FileMode]::Create)
# MiniDumpWithThreadInfo(0x1000)|MiniDumpWithUnloadedModules(0x20)|MiniDumpNormal(0)
$ok=[W.MD]::MiniDumpWriteDump($p.Handle,[uint32]$p.Id,$fs.SafeFileHandle.DangerousGetHandle(),0x1020,[IntPtr]::Zero,[IntPtr]::Zero,[IntPtr]::Zero)
$err=[Runtime.InteropServices.Marshal]::GetLastWin32Error()
$fs.Close()
if(-not $ok){throw "MiniDumpWriteDump failed, win32=$err"}
"DUMPED pid=$($p.Id) threads=$($p.Threads.Count) -> $Out $((Get-Item $Out).Length) bytes"
