OptiScaler 0.9.4 + DLSS5-AMD 0.23 组合包

已验证：RX 9070 XT、Windows、《剑星》游戏内 FSR3 输入。
OptiScaler 的 FSR2.1 和 FSR 3.x/4 后端均已接通 DLSS5 网络。
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
4. 在《剑星》中选择 FSR3 分辨率缩放，首次测试先关闭插帧，使用 900p 或 1080p 输出。
   黄色 DLSS5-AMD 帧率文字表示网络已运行。F6 切换 DLSS5 效果。

OptiScaler 设置
按 Insert 打开面板；没有 Insert 键可用 Win+Ctrl+O 打开 Windows 屏幕键盘，点 Ins。
本包默认 FSR 3.x/4。切换方法：左上选择后端 → Change Upscaler → Save Settings。
左上状态行显示当前实际后端；下拉框只是待应用选项。
游戏菜单的“FSR3”是输入接口，不代表 OptiScaler 最终执行的后端。
FSR2.1 在本次《剑星》场景略快（约38 vs 36fps，非严格同场景性能测试），可自行比较画质。
FSR 3.x/4 是后端选项名，不代表所有机器都必然启用 FSR4。
OptiScaler 0.9.4 的正确配置是 Dx12Upscaler=fsr31；不要照其旧说明改成 ffx，那个值会静默落到 FSR2.1。

分辨率和范围
网络默认按输入自动选择720/900/1080档，最大支持1920×1080；本包不是Magpie截图放大版。
DLSS5网络与0.23相同，默认跳过42/43/46块；900档插件显存约1.2GB。
其它游戏即使OptiScaler本身可用，仍可能需要适配DLSS5的资源格式、运动向量或提交时序。
联机反作弊游戏不要使用注入插件。

排错与卸载
反馈时提供游戏名、显卡、驱动版本、OptiScaler面板截图、OptiScaler.log、DLSS5-AMD\logs。
卸载时退出游戏，移除本包加入的文件，并还原安装前备份的同名文件；不能只删掉替换过的游戏DLL。
SHA256SUMS.txt为包内文件校验表，zip旁的.sha256为整个压缩包校验值。

来源
OptiScaler 0.9.4：https://github.com/optiscaler/OptiScaler/releases/tag/v0.9.4
对应源码：https://github.com/optiscaler/OptiScaler/tree/v0.9.4
DLSS5-AMD：https://github.com/lmxxf/dlss5-on-amd-9070xt-porting
OptiScaler、ReShade、MinHook与相关组件保留各自许可，见包内LICENSE文件与Licenses目录。
