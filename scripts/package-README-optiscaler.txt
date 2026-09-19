OptiScaler 0.9.4 + DLSS5-AMD 0.24.1 前置版组合包

与0.24的区别
补上配置/资产路径查找：DLL旁找不到DLSS5-AMD时，继续到游戏EXE旁找。
解决DLL被加载到_storage_等子目录后，误读旧配置或找不到权重的问题。
网络、权重、前置顺序与0.24不变；本修正不代表《生化危机9》已支持前置DLSS5。

与0.23的区别
顺序改为：游戏低分辨率颜色 → DLSS5 → OptiScaler的FSR 3.x/4后端 → 最终画面。
因此DLSS5的1080p输入上限不再等于游戏输出上限，可以尝试2K/4K输出。
修改的是DLSS5-AMD插件，OptiScaler本体、网络权重与HIP内核未变。
本版仍是前置路径的初步实现：DLSS5历史每帧重置，FSR自己的时序处理保留。

已验证：RX 9070 XT、Windows、《剑星》游戏内 FSR3 输入。
本版已验证：《剑星》2560×1440输出、FSR质量档，输入1707×961，实玩约34～35fps。
4K输出尚未实测；旧0.23上的FSR2.1结果不代表本版已逐项回归。
其他游戏尚未逐个验证；本包不是 OptiScaler 官方发行包。
需要 AMD 驱动自带 amdhip64_7.dll。网络内核针对 gfx1201（9070 XT）；不需要另装 HIP SDK。

安装
1. 退出游戏。先备份实际游戏 EXE 目录里的同名文件。
   《剑星》路径：StellarBlade\SB\Binaries\Win64。
2. 若之前安装过 DLSS5-AMD / ReShade / OptiScaler，先恢复或移走旧注入器和旧 addon，避免重复加载。
   本包 dxgi.dll 是 OptiScaler，ReShade64.dll 是 ReShade；只保留一份 dlss5-amd.addon64。
   我们早期测试版的 native-submission-order.addon64、native-present-contract.addon64 应移出目录。
   原来作为 ReShade 的 d3d12.dll 也应备份移走；不要误删游戏本身的系统运行库。
3. 将本包文件夹内的全部内容复制到实际游戏 EXE 旁，包括 DLSS5-AMD 文件夹。
   本包已配置好，不需要运行 OptiScaler 的 setup 脚本。
4. 在《剑星》中选择 FSR3 分辨率缩放，首次测试先关闭插帧。
   可以先试1920×1080，或已验证的2560×1440+FSR质量档。F6切换DLSS5效果。
   如显示状态文字，DLSS5 ON表示网络已处理输入；INIT是初始化中，OFF是旁路，UNSUPPORTED表示输入超限或格式不支持。
   状态也可查DLSS5-AMD\logs\native-pre-upscale.txt，持续出现processed=1、replay=0表示网络处理和超分派发正常。

OptiScaler 设置
按 Insert 打开面板；没有 Insert 键可用 Win+Ctrl+O 打开 Windows 屏幕键盘，点 Ins。
本包默认 FSR 3.x/4。切换方法：左上选择后端 → Change Upscaler → Save Settings。
左上状态行显示当前实际后端；下拉框只是待应用选项。
游戏菜单的“FSR3”是输入接口，不代表 OptiScaler 最终执行的后端。
本版先使用已验证的FSR 3.x/4，不建议拿旧版的FSR2.1帧率与这版不同分辨率直接比较。
FSR 3.x/4 是后端选项名，不代表所有机器都必然启用 FSR4。
OptiScaler 0.9.4 的正确配置是 Dx12Upscaler=fsr31；不要照其旧说明改成 ffx，那个值会静默落到 FSR2.1。

分辨率和范围
游戏输出分辨率可以高于1080p；送入DLSS5的低分辨率颜色仍须不超过1920×1080。
FSR的质量/平衡/性能档决定内部输入尺寸，网络再自动适配720/900/1080计算档。
例如2K质量档输入1707×961，网络使用1080档，然后FSR输出2560×1440。
尝试4K时，质量档通常会超过网络输入上限，需要降低到性能或超级性能；以日志render尺寸为准。
有些游戏会给内部尺寸多加一两像素，标称1080p也可能超限；超限时本版保留普通FSR，跳过DLSS5。
本包不是Magpie截图放大版。
DLSS5网络与0.23相同，默认跳过42/43/46块；900档插件显存约1.2GB。
其它游戏即使OptiScaler本身可用，仍可能需要适配DLSS5的资源格式、运动向量或提交时序。
前置路径依赖游戏命令列表的提交位置，目前只在《剑星》验证，不是所有游戏都能直接使用。
不要把本包配置复制给Magpie。新版DLL关闭DLSS5_PRE_UPSCALE时保留旧路径，但尚未做Magpie回归。
联机反作弊游戏不要使用注入插件。

排错与卸载
反馈时提供游戏名、显卡、驱动版本、OptiScaler面板截图、OptiScaler.log、DLSS5-AMD\logs。
卸载时退出游戏，移除本包加入的文件，并还原安装前备份的同名文件；不能只删掉替换过的游戏DLL。
SHA256SUMS.txt为包内文件校验表，zip旁的.sha256为整个压缩包校验值。

配置与回退
DLSS5-AMD\native-game-flags.txt中已设置DLSS5_PRE_UPSCALE=1和DLSS5_PRE_UPSCALE_ASYNC=1。
不要关闭异步提交；首版同步等待曾明显降低实玩帧率。
若要完全回退，请退出游戏后恢复旧0.23整包及其配置。将DLSS5_PRE_UPSCALE改0会走旧的超分后处理，此时游戏输出也必须降至1080p或以下。

来源
OptiScaler 0.9.4：https://github.com/optiscaler/OptiScaler/releases/tag/v0.9.4
对应源码：https://github.com/optiscaler/OptiScaler/tree/v0.9.4
DLSS5-AMD：https://github.com/lmxxf/dlss5-on-amd-9070xt-porting
OptiScaler、ReShade、MinHook与相关组件保留各自许可，见包内LICENSE文件与Licenses目录。
