param([switch]$FinalizeOnly,[string]$ConfigDirectory=(Join-Path $PSScriptRoot '..\..\scripts'))
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$g='C:\Program Files (x86)\Steam\steamapps\common\RESIDENT EVIL requiem BIOHAZARD requiem'
$r='D:\DLSSNR-Lab\re9-opti';$name='OptiScaler-REFramework-DLSS5-AMD-0.26.1';$stage="D:\給網友打包\$name";$zip="$stage.zip"
if(!$FinalizeOnly -and ((Test-Path $stage) -or (Test-Path $zip))){throw 'Output already exists'}
$addon='f7c10735b1447c7ed5ed29c92d3bc4e6a3a97a3583220a1e7ae515f4c0b6420a'
if((Get-FileHash "$g\re9-present.addon64").Hash -ne $addon){throw 'Wrong game-tested addon'}
$ref=Get-Content "$r\reframework-source.json" -Raw|ConvertFrom-Json
if((Get-FileHash "$g\dinput8.dll").Hash -ne $ref.dll_sha256){throw 'Wrong REFramework'}
if(!$FinalizeOnly){
if(!(Test-Path "$ConfigDirectory\hip-re9-flags.txt")){throw 'Missing repository RE9 configuration'}
$sourceManifest=Get-Content "$g\SHA256SUMS.txt"
# Use the original package inventory, never recursively copy a game directory.
$skip=@('README.txt','!! README_EXTRACT ALL FILES TO GAME FOLDER !!.txt','dlss5-amd.addon64','OptiScaler.ini','DLSS5-AMD\native-game-flags.txt','DLSS5-AMD\native-game-tiled-assets\native_codec_decode.hlsl','DLSS5-AMD\native-game-tiled-assets\native_text_overlay.hlsl')
$files=@()
foreach($line in $sourceManifest){if($line -notmatch '^([0-9a-fA-F]{64})\s+(.+)$'){throw 'Bad inventory'};$sha=$matches[1];$p=$matches[2].Replace('/','\');if($p -in $skip -or $p -like 'DLSS5-AMD\native-game-tiled-assets\HIP\*' -or $p -like '*\logs\*' -or $p -like '*\shader-cache\*'){continue};if((Get-FileHash "$g\$p").Hash -ne $sha){throw "Changed baseline payload $p"};$files+=$p}
New-Item -ItemType Directory $stage|Out-Null
foreach($p in $files){$dest="$stage\$p";New-Item -ItemType Directory -Force (Split-Path $dest)|Out-Null;Copy-Item "$g\$p" $dest}
foreach($p in @('OptiScaler.ini','fakenvapi.ini','dinput8.dll','re9-present.addon64','amd_fidelityfx_loader_dx12.dll','ReShadePreset.ini')){Copy-Item "$g\$p" "$stage\$p" -Force}
$a="$stage\DLSS5-AMD\native-game-tiled-assets";$ga="$g\DLSS5-AMD\native-game-tiled-assets"
foreach($p in @('native_codec_decode.hlsl','native_text_overlay.hlsl')){Copy-Item "$ga\$p" "$a\$p" -Force}
if((Get-FileHash "$a\native_codec_decode.hlsl").Hash -ne '98a790d928e61c3eab905f43374dc9a1e560aff22946cd17b166cd0ca3e6c5f8'){throw 'Wrong decoder'}
if((Get-FileHash "$a\native_text_overlay.hlsl").Hash -ne '8d20c7f5d9c08d4cc50ad726c4e31ba1dbf0b7281f5ecafeec8196defc997423'){throw 'Wrong overlay shader'}
$m='D:\DLSSNR-Lab\c256-frag-production-modules';$manifest=@(Get-Content "$m\SHA256SUMS");if($manifest.Count -ne 48){throw 'Wrong module count'}
foreach($line in $manifest){$p=$line.Substring(66).Replace('/','\');$dest="$a\HIP\$p";New-Item -ItemType Directory -Force (Split-Path $dest)|Out-Null;Copy-Item "$m\$p" $dest;if((Get-FileHash $dest).Hash -ne $line.Substring(0,64)){throw "Module mismatch $p"}}
Copy-Item "$ConfigDirectory\hip-re9-flags.txt" "$stage\DLSS5-AMD\native-game-flags.txt" -Force
'1'|Set-Content "$stage\DLSS5-AMD\re9-present-mode.txt" -Encoding ASCII
# Portable ReShade configuration; avoid user paths, layout and duplicate FPS overlay.
@'
[GENERAL]
EffectSearchPaths=.\
TextureSearchPaths=.\
PresetPath=.\ReShadePreset.ini
[INPUT]
KeyOverlay=36,0,0,0
[OVERLAY]
ShowFPS=0
ShowClock=0
ShowFrameTime=0
TutorialProgress=4
'@|Set-Content "$stage\ReShade.ini" -Encoding ASCII
Copy-Item "$r\REFramework-LICENSE.txt" "$stage\Licenses\REFramework-LICENSE.txt"
@'
OptiScaler-REFramework-DLSS5-AMD 0.26.1 完整包

适用：已在《生化危机9 / Resident Evil Requiem》、RX 9070 XT实玩通过。
带gfx1200/gfx1201内核；9060/XT仍待对应硬件反馈。
这是RE9后置兼容版，不是所有RE引擎游戏都已验证，也不替代通用OptiScaler 0.26。

安装
1. 完全退出游戏。将本包全部文件解压到re9.exe所在目录，允许覆盖本包文件。
2. 如果装过旧DLSS5插件，先移走根目录及_storage_中的dlss5-amd.addon64、re9-ffx-observer.addon64；仅保留本包re9-present.addon64。
   升级旧RE9测试版时，同步用本包re9-present.addon64覆盖_storage_里同名旧文件（若存在）。
   已有其他dinput8.dll模组时先备份，不能把两个代理DLL简单互相覆盖。
3. 游戏内选择DLSS超分，OptiScaler将其转接到FSR后端。可自由选超分质量。
4. 输出最高1920×1080，关闭HDR。2K/4K会显示错误并停止DLSS5处理。
   2K桌面建议使用1080P普通窗口；无边框可能仍输出桌面2K，以右上OUT显示为准。

实际流程
游戏低分辨率渲染 → FSR超分到≤1080P → DLSS5后处理。
模型固定以1600×900计算，再融合回保留的输出原图；包含UI，没有接入运动矢量历史。
NET是模型尺寸，不是游戏原生渲染尺寸；调整游戏超分质量不会改变NET。
当前固定900P，不要通过修改NETWORK_HEIGHT期待换档。

操作
F6：开关DLSS5处理。
F7：隐藏/恢复本插件全部信息（本次运行）。
Home：ReShade菜单。Insert：OptiScaler/REFramework菜单，默认按键可能同时响应。
DLSS5-AMD/native-game-flags.txt：SHOW_FPS=0关闭帧率行，NOTICE=0关闭状态/尺寸行（完整键名含DLSS5_前缀，每秒读取）。
Present FPS是插件观察的提交频率，不保证等于插帧后的显示帧率。
日志：DLSS5-AMD/logs。

0.26.1变化
新增RE9后置HIP兼容；R10G10B10A2/FP16转换；状态、分辨率和可隐藏的帧率信息；保留1080P输出保护，允许上游超分。
沿用0.26已验证的FFN直接片段、C256连续权重片段优化及双架构内核。
本包不含游戏程序、游戏资源、存档或本机游戏画质配置。不是补丁包，无需再下载模型。
'@|Set-Content "$stage\README.txt" -Encoding UTF8
$release=[ordered]@{version='0.26.1';variant='OptiScaler-REFramework';tested_game='Resident Evil Requiem';addon_sha256=$addon;reframework=$ref;network='1600x900';max_output='1920x1080 SDR';pipeline='game -> FSR -> HIP post-processing';modules=48}
$release|ConvertTo-Json -Depth 5|Set-Content "$stage\release.json" -Encoding UTF8
}
$a="$stage\DLSS5-AMD\native-game-tiled-assets"
if((Get-FileHash "$stage\re9-present.addon64").Hash -ne $addon){throw 'Staged addon mismatch'}
if((Get-Content "$stage\release.json" -Raw|ConvertFrom-Json).version -ne '0.26.1'){throw 'Wrong stage'}
New-Item -ItemType Directory -Force "$stage\DLSS5-AMD\logs"|Out-Null
'Runtime logs are written here.'|Set-Content "$stage\DLSS5-AMD\logs\README.txt" -Encoding ASCII
$readme=Get-Content "$stage\README.txt" -Raw
if($readme -notmatch 'amdhip64_7'){$readme+="`r`n运行环境：系统需提供HIP 7运行时（System32/amdhip64_7.dll）；本包不代替AMD驱动/运行时安装。不需要SM6.10预览驱动。`r`n";$readme|Set-Content "$stage\README.txt" -Encoding UTF8}
# Validate the actual staged shader set before compressing.
& 'D:\DLSSNR-Lab\compile_fit_shaders.exe' $a
if($LASTEXITCODE -ne 0){throw 'Staged shader validation failed'}
$all=@(Get-ChildItem $stage -Recurse -File|Where-Object{$_.FullName -ne "$stage\SHA256SUMS.txt"}|Sort-Object FullName);$hashes=@()
foreach($file in $all){$rel=$file.FullName.Substring($stage.Length+1);$hashes+=((Get-FileHash $file.FullName).Hash.ToLowerInvariant()+'  '+$rel)}
$hashes|Set-Content "$stage\SHA256SUMS.txt" -Encoding ASCII
if($FinalizeOnly -and (Test-Path $zip)){Remove-Item $zip}
$archive=[IO.Compression.ZipFile]::Open($zip,[IO.Compression.ZipArchiveMode]::Create)
try{foreach($file in Get-ChildItem $stage -Recurse -File){$rel=$file.FullName.Substring($stage.Length+1).Replace('\','/');$entry=$archive.CreateEntry($rel,[IO.Compression.CompressionLevel]::Optimal);$dst=$entry.Open();$src=[IO.File]::OpenRead($file.FullName);try{$src.CopyTo($dst)}finally{$src.Dispose();$dst.Dispose()}}}finally{$archive.Dispose()}
$archive=[IO.Compression.ZipFile]::OpenRead($zip)
try{foreach($line in $hashes){$p=$line.Substring(66).Replace('\','/');$entry=$archive.GetEntry($p);if(!$entry){throw "ZIP missing $p"};$stream=$entry.Open();$h=[Security.Cryptography.SHA256]::Create();try{$actual=([BitConverter]::ToString($h.ComputeHash($stream))).Replace('-','').ToLowerInvariant()}finally{$stream.Dispose();$h.Dispose()};if($actual -ne $line.Substring(0,64)){throw "ZIP mismatch $p"}};if($archive.Entries.Count -ne $hashes.Count+1){throw 'Unexpected ZIP entries'}}finally{$archive.Dispose()}
$ziphash=(Get-FileHash $zip).Hash.ToLowerInvariant();"$ziphash  $name.zip"|Set-Content "$zip.sha256" -Encoding ASCII
$result=[ordered]@{package="$name.zip";path=$zip;bytes=(Get-Item $zip).Length;sha256=$ziphash;payload_files=$hashes.Count;modules=48;addon=$addon;verified=$true}
$result|ConvertTo-Json|Set-Content "$r\release-0261.json" -Encoding UTF8
$result|ConvertTo-Json
