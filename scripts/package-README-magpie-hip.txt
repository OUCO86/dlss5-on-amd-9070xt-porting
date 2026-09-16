DLSS5-AMD 0.20 · Magpie 版（HIP 后端）
============================
整包文件：Magpie-DLSS5-AMD-0.20.zip

把 DLSS 5 的神经网络（DLSSNR）跑在 AMD RX 9070 XT（RDNA4）上，以 Magpie 窗口缩放器为载体：
支持宽不超过 1920、高不超过 1080 的普通游戏窗口，不需要游戏自己支持 FSR 或 DLSS。
本包固定用 1600x900 进行网络计算，建议游戏窗口设为 1600x900，再由 FSR4 放大到 2K/4K。
游戏窗口 -> FSR3（本插件的 DLSS5 入口）-> FSR4 放大到屏幕 -> XeSS 帧生成 -> 显示。
效果组里名叫 FSR3_SR 的那一项，就是本插件接入 DLSS5 的位置；界面名称仍是 FSR3，不用另外添加 DLSS5 滤镜。

0.20 与 0.15 的区别
--------
  推理后端从 DirectX 12 Shader Model 6.10 换成了 AMD HIP：网络的 24 个内核以 GPU 原生二进制（.hsaco）随包提供，
  由显卡驱动自带的 HIP 运行时执行，输出与 0.15 逐位相同（同一输入、同一种子、同一历史帧，40 帧输出哈希完全一致）。
  因此不再需要：预览驱动的 Shader Model 6.10、DirectX Agility SDK 1.721 预览运行时、Windows 开发人员模式。
  速度：独立测试台 1600x900 每帧约 15.5ms（0.15 为 16.8ms）；《剑星》游戏内 900p 实测约 52 fps（0.15 约 47）。
  Magpie 路径的实机测试在发布前由作者完成，见下方「已知」。

本包内容
--------
  Magpie.exe 及其文件            Magpie 实验分支 0.6.6（SAOG0721/Magpie，GPL-3，许可见 LICENSE-Magpie.txt；A 卡用不到的 NVIDIA 运行库已去掉）
  config\config.json             Magpie 便携模式配置（预设好的效果组和选项）
  dxgi.dll                       ReShade 6.8 加载器（原版，未修改；放在 Magpie.exe 旁边就会被加载）
  dlss5-amd.addon64              本移植的 DLL（.addon64 是 ReShade 的扩展名，不要改名）
  DLSS5-AMD\                     权重、HIP 内核（native-game-tiled-assets\HIP\ 里 24 个 .hsaco）、运行参数（必须和 dlss5-amd.addon64 在同一目录）
  SHA256SUMS.txt                 文件校验

需要
----
  1. RX 9070 / 9070 XT（RDNA4）。内核只编了 gfx1201，RX 7000 不支持。
  2. 显卡驱动带 HIP 7 运行时：C:\Windows\System32\amdhip64_7.dll 存在即可。
     已验证的是 AMD 预览驱动 32.0.31007.2048（0.15 要求的那个）；正式版驱动只要 System32 里有 amdhip64_7.dll 理论上同样可用，
     但还没有实测。初始化失败时看 DLSS5-AMD\logs\native-game-oneshot.txt 里 HIP 相关的行。
     不再需要开发人员模式，不需要装 HIP SDK、SM 6.10 编译器或任何 SDK。
  3. 游戏选择窗口模式，宽不超过 1920、高不超过 1080；普通窗口和无边框窗口都可以。
     若看到 "DLSS5-AMD: INPUT MAX 1920X1080 (NOW WxH)"，请减小游戏窗口，并确认效果组第一站 FSR3 没有提前放大。

安装（整包版：Magpie 本体已经在里面，解压即用）
----
  1. 解压到任意目录（路径别带中文），运行 Magpie.exe。便携配置随包，选择效果组 "DLSS5-AMD" 即可。
     已预设 FSR3_SR -> FSR4_SR -> XeSS_FrameGeneration_x2_ZeroMV。
     光流默认只在第一项 FSR3（DLSS5）开启 AMDOF；FSR4 和 XeSS 插帧的 Optical Flow Method 均选 None。
     如果自己调整效果组：FSR3 的缩放选相对于输入尺寸、水平/垂直均 1 倍；FSR4 选充满屏幕。不要把 FSR3 设成适应屏幕。
     不需要插帧时，删掉最后的 XeSS_FrameGeneration_x2_ZeroMV 即可。
  2. 游戏选择窗口模式，建议 1600x900；也接受不超过 1920x1080 的窗口，实际尺寸略小没关系。
  3. 回到游戏，按 Alt+Shift+A 激活缩放。初始化通常需要 3～5 秒。
     左上角先显示 "DLSS5-AMD: INITIALIZING..."，接管后显示网络自己的 FPS 和耗时。
     若显示 "INIT FAILED - SEE DLSS5-AMD\LOGS"，先确认 System32 里有 amdhip64_7.dll。
     再按一次 Alt+Shift+A 停止缩放，可以对比原图。
  从 0.15 升级：直接换整个目录；旧包的 DLSS5-D3D12-721 和 enable-game-sdk721.txt 在 0.20 里没有了，属正常。

已知
----
  - 计算档位：native-game-flags.txt 中 DLSS5_NETWORK_HEIGHT=900（可改 720/900/1080，完全退出并重启 Magpie 生效）。
  - 小窗口适配默认开启（DLSS5_FIT_INPUT=1），FPS 和 XeSS 帧生成也默认开启。
  - 输入是显示用的 8 位 sRGB 图；插件按 sRGB 直通处理（DLSS5_CODEC_SRGB=1），亮度和原图一致。
  - DLSS5（第一项 FSR3）的运动向量来自 Magpie 的光流估计（AMDOF）；超过 64 像素的向量当静止处理（DLSS5_MOTION_MAX_PX）。
  - 强度：native-game-flags.txt 里加一行 DLSS5_STRENGTH=<细节>,<颜色>（各 0～1，默认 1,1）。改完重启 Magpie 生效。
  - 停止缩放再激活，插件会重新接管（需要重新初始化）。
  - 日志：DLSS5-AMD\logs\native-game-oneshot.txt（初始化）、native-submission-order.txt（每帧观察）。
  - 屏幕提示不想要：加一行 DLSS5_NOTICE=0；帧率不想看：删掉 DLSS5_SHOW_FPS=1。
  - F6 是本插件的开关键（全局）；如果同一台机器上游戏里也装了本插件的游戏版，两边会一起切。

卸载
----
  整个目录删掉即可，不写注册表、不碰 AppData。

来源
----
  https://github.com/lmxxf/dlss5-on-amd-9070xt-porting（源码、每个 tag 的改动、开发记录）
