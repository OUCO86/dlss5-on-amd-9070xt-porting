# DLSS 5（DLSSNR）跑在 AMD RX 9070 XT 上

[English](README.md)

把 NVIDIA DLSS 5 的神经渲染器（`nvngx_dlssnr.dll` 里那张 71 块的 Swin/ViT 网络，"DLSSNR"）逐块逆向，用
Direct3D 12 从零重写成 Shader Model 6.10 wave-matrix（`dx::linalg`）+ FP8（E4M3）的 HLSL 计算着色器，在 AMD RDNA 4
显卡上跑起来，并通过 ReShade 插件钩住游戏的 FSR dispatch，对 1080p 画面做后处理。

**REFramework 专用版（0.28.1）**：针对《生化9》特殊提交方式，采用配套的修改版OptiScaler宿主和`LmxxfNrRuntime.dll`，流水线为游戏渲染→HIP DLSS5→FSR→显示。已验证2K无边框输出，并补上同帧曝光归一化/还原。神经输入仍须≤1920×1080，网络按输入自动选择档位。0.28.1在初始化前拒绝超限输入并保留原始超分，修复初始化失败后换回有效尺寸无法恢复的问题。旧RE9 0.28已撤下。F6由新宿主管理，旧后置addon停用；其他RE游戏（包括旧版已测的Xbox《鬼武者》）需重新验证，不能沿用0.27兼容结论。

**最新（2026-09-22，常规包0.28／RE9专用包0.28.1）**：三个完整包更新共享HIP核的六项无损优化：RGB末端共用读取、C128/C256全零填充快路径、ViT展开/投影与解码器投影固定尺寸优化。《剑星》实玩无明显异常，画面和帧率基本不变；不承诺固定提升。常规两包沿用原宿主，RE9特殊包采用新前置宿主并修复曝光遗漏。未新增有损优化；完整模型及gfx1200/gfx1201模块随包，自适应复用在常规包默认关闭。

**默认配置**：新包自动带入仓库中的[普通游戏配置](scripts/hip-game-flags.txt)、[Magpie配置](scripts/hip-magpie-flags.txt)或[REFramework配置](scripts/hip-re9-flags.txt)，不继承本机试玩设置。来源与打包方法见[配置说明](scripts/CONFIGURATION.md)。

**常规addon开启自适应复用（不适用于0.28 RE9 runtime）**：在游戏目录的`DLSS5-AMD/native-game-flags.txt`中将`DLSS5_VIT_ADAPTIVE=0`改为`1`，并设置`DLSS5_VIT_REUSE_HOTKEY=1`、`DLSS5_HIP_GRAPH=0`、`DLSS5_HIP_VIT_BYTE_STREAM=0`，重启游戏。F8切换复用/完整计算；F8不取消原有跳层配置。精确流式注意力直接生效，无需开关。机制和限制见[ViT复用说明](Development/HIP/VIT-REUSE.md)。

**现状（2026-09-17，`0.20`，HIP 后端）**：推理后端从 DirectX 12 Shader Model 6.10 wave matrix 换成 AMD HIP——网络的 24 个内核以 gfx1201 二进制（`.hsaco`）随包提供，由 AMD 驱动自带的 HIP 7 运行时（`amdhip64_7.dll`）执行。输出与 0.15 的 DX12 链逐位相同（40 帧输出哈希一致）；独立测试台 1600×900 每帧 16.8 → ≈15.5 ms，《剑星》游戏内 900p 47 → 52 fps。不再需要 Agility SDK 1.721 预览运行时、Shader Model 6.10 和 Windows 开发人员模式。下面的 DX12 链作为历史记录保留。

**现状（2026-09-13，Magpie 整包 `0.15`）**：RX 9070 XT 上支持**宽不超过 1920、高不超过 1080** 的普通游戏窗口。窗口比 1080p 小几个像素也能自动适配，保持原有宽高比；处理后由 FSR4 放大到屏幕，保留 XeSS 帧生成（ZeroMV）。游戏不需要原生支持 FSR/DLSS。

用户实玩《鬼武者》：1080p 窗口放大到 2K，保持约 **30 帧**。另用测试窗口在 4K 桌面验证，网络约 **29 fps**；这是两种场景，不是插帧前后的对比。

**效果组里的 `FSR3_SR` 就是 DLSS5 的入口**：插件在这一项接入 DLSS5，界面仍显示 FSR3；不用再找或添加单独的 DLSS5 滤镜。第一项保持输入尺寸，后面的 FSR4 负责放大。光流只在第一项选 AMDOF；FSR4 和 XeSS 插帧的 Optical Flow Method 选 None，避免额外光流造成发糊。

便携预设为 **FSR3（由本插件接入 DLSS5）→ FSR4 充满屏幕 → XeSS 帧生成**。默认开启小窗口适配（`DLSS5_FIT_INPUT=1`）和网络帧率显示，FPS 数字至少间隔三秒刷新。

0.20（HIP）只要驱动带 `amdhip64_7.dll`（我们在 AMD 32.0.31007.2048 预览驱动上验证；正式版驱动同样带这个文件，2026-09-17 有用户反馈正式版可用）。0.15 及之前的 DX12 版需要 Windows 开发人员模式和 AMD 26.10.07.02 预览驱动。HIP 插件 900p 实测占显存 1.2GB（权重 0.6GB、激活 0.3GB、共享缓冲 0.07GB 加运行时开销；`DLSS5_HIP_MEMORY=1` 会把明细写进 `logs\native-hip.txt`）。显存被顶满仍会掉帧且不恢复；《星刃》游戏内钩子版的贴图质量应选「高」或更低。0.22 起 900 档把 1600×900 补到 960 行而不是 1024 行（60 行反射 + 一行零 ViT token，和 1080 档补 token 网格的做法一样）：内核不变、少算约 6%（15.2 → 14.4ms），输出与 0.21 的布局不同（31.5dB），两者都没有参考可言对错；0.21 的布局保留为 `DLSS5_NETWORK_HEIGHT=900w`，也仍是逐位黄金值的测试台几何（960 行的黄金值在 `Development/HIP/validate-modules-960.ps1`）。`DLSS5_NETWORK_HEIGHT=auto` 按输入窗口自动选网络档位（≤1280×720 走 720，≤1600×900 走 900，其余走 1080，超过 1920×1080 拒绝），左上角帧率后面显示实际档位（如 `1600X900`）；写 720/900/1080 则固定。画质/速度档位由 `native-game-flags.txt` 里的 `DLSS5_SKIP_BLOCKS` 决定：不写 = 全网络；`42,43,46`（默认）约 −1ms、约 41dB；`12,28,41,42,43,44,46,52,53`（性能档）900p 再 −0.8ms（15.25 → 14.48ms，2026-09-17 ABBA），相对默认输出约 30dB。`scripts/game-flags.txt` 和 `scripts/magpie-flags.txt` 分别记录两种运行配置，`scripts/bench.ps1` 编译配套 shader。安装方法见 [Magpie 包内说明](scripts/package-README-magpie.txt)。

## 仓库结构

| 目录 | 内容 |
|---|---|
| `src/` | 常规 ReShade addon、图像编解码与游戏接入；Magpie和普通OptiScaler共用这套addon源码。 |
| `hip/` | 共用HIP网络计算核、gfx1200/gfx1201编译配方；三包共用同一网络源码。 |
| `shaders/` | 图像编码/解码、拷贝等配套HLSL，以及历史DX12网络实现；HIP版也需要部分shader。 |
| `scripts/` | 常规addon编译、发布配置和包内说明；`hip-game-flags.txt`、`hip-magpie-flags.txt`为常规包默认配置，`re9-presr.ini`为新RE9宿主覆盖配置。 |
| `Development/HIP/` | HIP宿主、D3D12互操作、离线验证；`experiments/`是未必采用的实验。这里部分代码参与编译。 |
| `Development/RE9/presr/` | RE9专用OptiScaler/runtime适配：锁定的上游版本、补丁、准备/构建/安装脚本及测试。完整上游源码不在本Git里。 |
| `Development/tools/` | 完整包组装脚本，按已校验框架底包加入DLL、shader、模型与双架构内核。 |
| `Development/results/`、`Development/deployments/` | 回归/性能证据及部署清单。 |
| `Development/DevHistory.md` | 已完成工作的开发日志；方案、实验限制和待办在对应专题文档。 |
| `tools/` | 输出对照、图像统计等辅助工具。 |

**源码与完整包分开管理。** Git管理我们自己的addon/runtime/HIP代码，以及RE9宿主的适配补丁；不包含完整Magpie或普通OptiScaler框架源码，也不包含可重打全部整包所需的模型权重和框架底包。RE9宿主基于[TheAutomatic的release/1.9.0](https://github.com/TheAutomatic/dlss-5-amd-project/tree/release/1.9.0)，`upstream.json`锁定版本，`prepare-host.py`应用适配；其GPL许可与本项目MIT代码分别保留。

维护机分工：Linux工作区保存本仓库；9070的Windows端保存框架底包、模型和构建产物。当前完整发布目录是`D:\給網友打包`；RE9完整宿主源码/产物在`D:\DLSSNR-Lab\re9-presr\source`和`bin`，HIP实验产物在`D:\DLSSNR-Lab\hip-backend`。这些是维护机路径，不是用户安装时要创建的目录。新包从已校验ZIP构建，不从正在玩的游戏目录打包。

三种接入关系：**Magpie/普通OptiScaler → dlss5-amd.addon64 → 共用HIP核**；**RE9专用OptiScaler → LmxxfNrRuntime.dll → 同一套HIP核**。RE9宿主和runtime必须成对使用。

## 原理概要

- **网络**：pre 块（C32 @1920×1152）→ 编码器（C32 ×4、C64 ×4、C128 ×6、C256 ×8、C512 ×8）→ 8 个全局 ViT 块
  （640 token × 1024）→ 解码器（C512 → C32，带跳连）→ 第 70 块 post → RGB 头。8×8 窗口注意力，4 倍隐层 FFN，
  f16 残差流在块间量化到 E4M3。
- **核**：所有 GEMM 都是 wave-matrix 乘（A 16×32、B 32×16、f32 累加器），E4M3/f16 操作数直接从显存加载；行归约
  （归一化、softmax 分母）用对全 1 tile 的 MMA 完成；量化用硬件 `Cast<F8_E4M3FN>`。C32 注意力把两个窗口的
  QKV + 注意力 + 投影放在一个 256 线程组里做完。
- **游戏侧**：插件钩住 FSR dispatch，编码画面，用运动向量采样上一帧网络输出（时序 history），网络走延迟提交环
  （每帧 6 个命令列表），结果拷回。输出侧有一个小的时间平滑 pass（`native_output_smooth.hlsl`），压网络在抖动边缘
  周围产生的闪烁。
- **数值**：一条"精确链"逐位复现 NVIDIA 的核（每步显式 f16 舍入）；快速链放宽（f32 累加、硬件舍入），用 PSNR
  对精确链校验。

## 编译

### HIP 版（0.20）

需要：Linux / WSL 上的 `x86_64-w64-mingw32-g++`、ReShade 6.8 插件头文件、MinHook 源码（编 DLL）；一台装着 AMD 驱动、System32
里有 `amd_comgr_3.dll` 和 `amdhip64_7.dll` 的 Windows 机器（编内核；不用 HIP SDK、不用 DXC、不用开发人员模式）。插件的 DX12
侧还有几个小的 HLSL（编解码、屏幕文字）在运行时用系统自带的 `d3dcompiler` 编，任何 Windows 都有。

```bash
bash scripts/build-addon.sh <minhook源码目录> <reshade的include目录> dlss5-amd.addon64 --hip   # 插件，HIP 后端
x86_64-w64-mingw32-g++ -std=c++17 -O2 -static hip/rtc_compile.cpp -o hip/rtc_compile.exe   # 内核编译器
```

```powershell
# AMD 机器上：全部 24 个模块 -> <out>\*.hsaco + modules.json + SHA256SUMS（约一分钟）
powershell -ExecutionPolicy Bypass -File hip\build-modules.ps1 -OutputDir <out>
```

模块装到权重旁边的 `DLSS5-AMD\native-game-tiled-assets\HIP\`（或用 `DLSS5_HIP_MODULES` 指向目录）。
`Development/HIP/validate-modules.ps1` 对一套模块跑三道逐位校验；`Development/HIP/package-hip.ps1` 组装游戏包和 Magpie 包。
配方规则见 `hip/README.md`。

### DX12 版（0.15 及之前）

需要：Linux 上的 `x86_64-w64-mingw32-g++`（交叉编译）；Windows + RDNA 4 显卡 + 暴露 D3D12 wave matrix（linalg
tier 10）的驱动；Shader Model 6.10 预览版 `dxc`（带 `dx/linalg.h`）；ReShade 6.8 插件头文件；MinHook 源码。

预览版组件从哪来（都链在微软那篇 [Announcing Agility SDK 1.721 preview and more Shader Model 6.10 features](https://devblogs.microsoft.com/directx/announcing-agilitysdk-721-preview-and-more-shader-model-6-10-features/)）：预览版 DXC 是 [microsoft/DirectXShaderCompiler](https://github.com/microsoft/DirectXShaderCompiler/releases) 的 *preview* 发布（我们用 v1.10.2605.24，`dxc_preview_2026_05_22.zip`，解压到任意目录作为 `-DxcRoot`）；Agility SDK 运行时（`D3D12Core.dll`，包里的 `DLSS5-D3D12-721` 文件夹）是 NuGet 包 `Microsoft.Direct3D.D3D12` 1.721.3-preview；AMD 驱动是 RC「Agility SDK」版 26.10.07.02（32.0.31007.2048），不是正式版：[AMD 官方下载](https://drivers.amd.com/drivers/amd-software-adrenalin-edition-26.10.07.02-win11-rc7-agility-sdk.exe)。

**Windows 开发人员模式必须打开**（设置 → 系统 → 开发者选项）：插件靠 `D3D12EnableExperimentalFeatures` 打开实验性着色器模型，这个调用只在开发人员模式下成功；关着的话初始化停在第一步（`logs\native-submission-order.txt` 里 `sdk721_before_device ... experimental=` 后面不是 `00000000`）。跑发布包不需要再装别的东西：着色器是编好的，不用 DXC、HIP、任何 SDK。

```bash
# 一键（Ubuntu / WSL）：sudo apt install g++-mingw-w64-x86-64 git；自动把 MinHook 和 ReShade 头文件拉到 third_party/
bash scripts/build-addon-oneclick.sh            # 产出 native-game.addon64
# 或者手动
bash scripts/build-addon.sh <minhook源码目录> <reshade的include目录> native-game.addon64 --tiled
bash scripts/build-bench.sh native-network70-temporal.exe
```

```powershell
# 只编 shader，任意 Windows x64 机器（需要 SM 6.10 预览版 dxc 包；不需要显卡和权重）
powershell -ExecutionPolicy Bypass -File scripts\compile-shaders.ps1 -Folder D:\dlss5-shaders -DxcRoot <dxc-preview>
# Windows 侧：<lab> 目录放着色器、权重和测试台 exe
powershell -ExecutionPolicy Bypass -File scripts\bench.ps1 -Folder <lab> -DxcRoot <dxc-preview>
powershell -ExecutionPolicy Bypass -File scripts\deploy_fast.ps1 -Source <lab> -Dll native-game.addon64 -Flags scripts\game-flags.txt
```

## 更新记录

除注明 Magpie 场景的记录外，帧率为《星刃》1920×1080、RX 9070 XT；「测试台」是只跑网络的离线程序。0.01 之后的每个 tag 都以逐位精确的参考链为裁判（对它约 42 dB PSNR）；下面写「逐位相同」指快速链自己的输出一位都没变。

| 版本 | 日期 | 做了什么 | 结果 |
|---|---|---|---|
| `0.01` | 09-08 | 精确移植终点：71 块全部走 wave 矩阵核，15 帧与原版逐位一致；权重常驻显存（不再每帧过 PCIe）；块间共享 scratch（14.7 → 7.3 GB） | 测试台 186 ms，游戏约 5 fps |
| `0.02` | 09-08 | 快速链开始（精确链冻结当裁判）：FP32 硬件累加、E4M3 操作数、激活收尾和注意力去掉中间 f16 舍入；游戏里接上时序（运动向量 + 上一帧输出） | 测试台 112 ms，约 8 fps |
| `0.03` | 09-08 | 硬件 f16/E4M3 转换、QKV+归一化合核、C32 注意力两个 dispatch、ViT 打包输入、C512 直接注意力、多头块 FP8 残差流 | 测试台 62.7 ms，约 15 fps |
| `0.04` | 09-09 | 延迟提交环、命令列合批（每帧约 100 → 25 列）、C32 注意力并入 QKV、噪声前缀改 ALU 生成（去掉 200 MB 表）、ViT QKV 合核 | 游戏 GPU 32 ms，23～25 fps |
| `0.05` | 09-09 | 输出侧时间平滑（雨景闪烁）、C32 注意力一组两窗、ViT 注意力走 FP8 | 24～25 fps |
| `0.06` | 09-09 | 仓库重整（`src/ shaders/ scripts/`），`bench.ps1` 拍平 76 层 runner，每帧 GPU 探针默认关（它的 Flush 占 3 ms），pre 块输出 E4M3 | 27～28 fps |
| （0.07） | 09-09 | 只发了用户包没打 tag：跳过三块（40.7 dB）、显存 6.8 → 3.75 GB 并周期 MakeResident、C32 中间量 f16、post 块 merge 折进 FFN | 29 fps |
| `0.08` | 09-10 | C32 FFN 并进注意力序言；ViT / C512 / 解码器入口权重改非 2 的幂步长的 tile 布局；C512 FFWD 输出 E4M3 tile 直读、C512 块直接按 raster 读写并以 E4M3 流相连（去掉窗口 pack/crop 和 QKV pack）；post merge 每次 Load 四通道；解码器投影收尾连续写——全部逐位相同。《浪人崛起》走 XeSS 路径（钩 `xessD3D12Execute`）。指令级工具链（无界面 RGP 抓取、ISA 统计）。黑帧探针。贴图质量「高」或更低成为明确要求 | 测试台 24.4 ms，显存 3.1 GB，36～37 fps |
| `0.09` | 09-11 | 升采样投影 56/62/66 输出 f16 光栅、下游首块直读（逐位相同，−0.2 ms）。**Magpie 版**：插件不再限定进程（写死的 exe 白名单在别的游戏里就是 ReShade 的 1114 错误，已去掉）、也钩 FSR 4 SDK loader 的 `ffxDispatch`、接受 8 位 UNORM 贴图、运动向量按 dispatch 的 `motionVectorScale` 换算、接管帧可配（`DLSS5_SNAPSHOT_FRAME`），于是能跑在 SAOG0721 的 Magpie 实验分支的 FSR3 效果里：任何能开 1920×1080 无边框窗口的游戏都能用，不需要游戏支持 FSR/DLSS（约 30 fps；输入是 8 位 sRGB 成品图，画面比游戏内钩子版更白）。ViT expand+contract 合核试过被否（慢一倍，延迟受限） | 测试台约 24.2 ms，游戏内 36～37 fps；Magpie 约 30 fps |
| `0.10` | 09-11 | 黑块根因修掉：硬件 E4M3 转换不饱和，残差超 ±448 变 NaN，NaN token 扩散到整个 8×8 注意力窗口，rgb 头 clamp 成 0。融合 C32 块在硬件转换前夹到 ±448（`DLSS5_BUILD_C32_SAT_CAST`：FFN 输入/隐层/注意力输入/AV 输出）。参考 fixture 逐位不变；Magpie 转储帧头部 NaN 25920 → 0。文档补上 Windows 开发人员模式（`D3D12EnableExperimentalFeatures` 需要）。Magpie 包 `Magpie-DLSS5-AMD-0.10.zip` | 不变 |
| `0.11` | 09-11 | 接管时间 20～30 秒 → 约 3.5 秒：add-on 加载时后台预读权重进内存（`NativePrefetchWeights`）、约一千张常驻权重表的拷贝合成一批只等一次 GPU（`NativeResidentBatch`；第一版提前释放了拷贝目标把 GPU 挂了，现在源和目标都扣到 flush 之后）、六个运行时编译的 shader 落磁盘缓存（`shader-cache\`）、f16 权重展开 8 线程。数值不变（参考 fixture 逐位相同）。初始化计时探针（`DLSS5_VRAM_LOG=1` / `DLSS5_INIT_LOG=<file>`）。两遍 C32 softmax 试过关掉（null：那 896 字节 scratch 属于一个从不派发的 PSO，融合核本身没有溢出）。Magpie 包 `Magpie-DLSS5-AMD-0.11.zip` | 不变 |
| `0.12` | 09-12 | 屏幕提示（`native_text_overlay.h` / `.hlsl`）：上采样输出不是 1920×1080 时（2K/4K 屏 Magpie 选了适应屏幕，或游戏窗口不是 1080p）插件不再默默旁观，直接把 "DLSS5-AMD: INPUT MUST BE 1920X1080 (NOW WxH)" 写进画面；接管的 3～5 秒显示 "INITIALIZING..."，初始化失败（开发人员模式没开、驱动不对）显示 "INIT FAILED - SEE DLSS5-AMD\LOGS"。5×7 点阵字体画进自己的缓冲再拷进宿主贴图，在游戏那批命令之后用自己的命令列表提交（对宿主贴图建 UAV、或往游戏的命令列表里录命令，在 Magpie 里都会让 D3D12Core 崩）。flag 文件里 `DLSS5_NOTICE=0` 关掉。另：`DLSS5_OVERLAP`（网络放自己的计算队列、落后一帧；这张卡上 null，默认关）、`DLSS5_BUILD_C32_LDS_SLIM`（融合 C32 核少用 4KB LDS；逐位相同、无收益，默认关）。数值不变。Magpie 包 `Magpie-DLSS5-AMD-0.12.zip` | 不变 |
| `0.13` | 09-12 | `DLSS5_SHOW_FPS=1`（Magpie 包默认开）：网络自己的帧率用提示字体画在角上。钩子按游戏声明的输出状态接管（映射 ffx_api 状态位），不再只认 UAV。pre 块错误带源码行号。踩坑记录：Windows Update 会悄悄把预览驱动换成正式驱动（SM 6.10 没了，每个 PSO 都 E_INVALIDARG，屏幕写 INIT FAILED）——重装 26.10.07.02，并设 `ExcludeWUDriversInQualityUpdate=1`。Magpie 包的效果组在 FSR3_SR 后面挂了 XeSS 帧生成（ZeroMV，跨厂商）：9070 XT 上网络 28 帧、显示 55 帧，多一帧延迟，网络本身在光流旁边慢 20% 左右。数值不变。Magpie 包 `Magpie-DLSS5-AMD-0.13.zip`（sha256 9104C48D…） | 不变 |
| `0.14`（整包） | 09-12 | FPS 数字至少三秒刷新一次，不变的字条直接复用，贴字并入已有输出提交，去掉单独的同步提交。保留 XeSS FG ZeroMV 预设。整包清理备份 DLL、日志及 shader 缓存，重新生成文件校验清单。`Magpie-DLSS5-AMD-0.14.zip`，358,004,639 字节；SHA256 `14ccde3c752b40821cb9f30024579304627a2499e087e06e9aec399bfe734eed`。尚未打 0.14 tag。 | 编译通过；671 个包内文件校验通过；帧率收益未测 |
| [0.15](https://pan.quark.cn/s/1601ca8f80ae) | 09-13 | 普通窗口宽≤1920、高≤1080 即可输入，按原宽高比适配固定网络尺寸，再还原窗口尺寸交给 FSR4。便携预设：FSR3（DLSS5 入口）→ FSR4 充满屏幕 → XeSS FG ZeroMV。默认 `DLSS5_FIT_INPUT=1`，保留三秒刷新 FPS。整包 `Magpie-DLSS5-AMD-0.15.zip`。  358,010,545 字节；SHA256 `9bb7a021d09d987986f96dbd920589018606c9800dbd08e007f4b309388e5909`。| 672 个包内文件校验通过；《鬼武者》中画质2K约30帧 |
| [0.15-900P](https://pan.quark.cn/s/a5339e4c8549) | 09-14 | 固定1600×900内部计算（处理1600×1024、400个ViT位置），再经FSR4放大；仅第一项DLSS5/FSR3开启AMD光流。用户实玩：效果比720p更好、帧率较稳，1080p加插帧不稳。独立900p推理约16.71ms，不是游戏帧率。整包 `Magpie-DLSS5-AMD-0.15-900P.zip`，358,038,890字节，SHA256 `718d77941674d6e851e7babc14b40a596da52e86aec603f44f956b99ff6811d5`。 | 用户实玩900p通过；676个包内文件校验通过 |
| [0.20](https://pan.quark.cn/s/3c8b5329353c)（HIP） | 09-17 | HIP 后端：COMGR 编译的 gfx1201 内核（源码与构建配方在 `hip/`，实验在 `Development/HIP/`）、D3D12↔HIP 共享缓冲/围栏，与 DX12 链逐位一致。09-16/17 两天的核内工作（读 ISA 找病：转换函数去分支、load 连发、别名重载提出循环、残差对角片预打包、prefix 内联）把独立 900p 帧从 19.4 压到 ≈15.5 ms，比 DX12 链快 8%；游戏内 900p 52 fps。包：`DLSS5-AMD-0.20.zip`（游戏版）、`Magpie-DLSS5-AMD-0.20.zip`（Magpie 版，不含 Agility 运行时）。需要驱动自带 `amdhip64_7.dll`。|
| [0.21](https://pan.quark.cn/s/85a507a744bd)（HIP） | 09-17 | `DLSS5_NETWORK_HEIGHT=auto`：按输入窗口自动选网络档位（≤1280×720 走 720，≤1600×900 走 900，其余 1080），左上角帧率后显示档位（`1600X900`）；包内说明：显存实测 1.2GB、正式版驱动已有用户反馈可用、性能档（`DLSS5_SKIP_BLOCKS` 九块，−0.8ms、约 30dB）。内核、权重、输出与 0.20 逐位相同。实玩 900p 52～54 fps，1080p 37～38 fps。包 `DLSS5-AMD-0.21.zip`（sha256 38e15189…）、`Magpie-DLSS5-AMD-0.21.zip`（sha256 8eeee2dd…）。 |
| [0.22](https://pan.quark.cn/s/03f9995d0551)（HIP） | 09-17 | 900 档补边 1024 → 960 行（60 行反射 + 一行零 token，与 1080 档同一套做法）：内核不变，−0.9ms（6%，同批 15.8 → 14.9ms；机器空闲时约 14.4ms），900p 约 +3 帧。输出与 0.21 不同（31.5dB，两种布局都是自定义的）；`DLSS5_NETWORK_HEIGHT=900w` 回到 0.21 布局。960 行黄金值见 `validate-modules-960.ps1`。包 `DLSS5-AMD-0.22.zip`（sha256 59226956…）、`Magpie-DLSS5-AMD-0.22.zip`（sha256 8186b67d…）。 |
| 0.23 · [Magpie](https://pan.quark.cn/s/548e52cc4f49) · [OptiScaler](https://pan.quark.cn/s/8b5a402012a2)（HIP） | 09-18 | 修复带核显（AMD Radeon(TM) Graphics）或第二块显卡的机器初始化失败（画面 INIT FAILED，日志 `bridge currently requires exactly one HIP GPU`，2026-09-18 用户反馈）：桥接改为枚举 HIP 设备，选与游戏 D3D12 适配器同名的那块（取第一个匹配；两块同型号卡仍会选第一块）。单卡机器不变，内核、权重、输出与 0.22 逐位相同（《剑星》1080p 37 帧、900p 52 帧复测）。包 `DLSS5-AMD-0.23.zip`（sha256 3dde0e0a…）、`Magpie-DLSS5-AMD-0.23.zip`（sha256 7146569c…）。09-19 新增 `OptiScaler-DLSS5-AMD-0.23.zip`（sha256 9d70d28f…）：OptiScaler 0.9.4 + ReShade + 同一套 0.23 HIP 插件，《剑星》FSR 输入下已验证 FSR2.1、FSR 3.x/4 两种后端；默认 FSR 3.x/4、关闭插帧，其他游戏尚未验证。 |
| 0.24 · [OptiScaler](https://pan.quark.cn/s/1f32ffbd2e96)（HIP） | 09-19 | 前置版：游戏低分辨率颜色 → DLSS5 → OptiScaler 的 FSR 3.x/4 → 最终输出。修改我们自己的插件，OptiScaler 本体、网络权重与内核不变；采用同队列异步提交。《剑星》2560×1440、FSR质量档（输入1707×961）实玩约34～35帧。DLSS5历史暂时每帧重置，FSR时序处理保留；网络输入仍须≤1920×1080，4K输出与新版DLL的Magpie回归尚未验证。包 `OptiScaler-DLSS5-AMD-0.24.zip`（385,880,495字节，sha256 2a46adeb…）。 |
| 0.24.1 · [OptiScaler](https://pan.quark.cn/s/4f73a54d0ff9)（HIP） | 09-19 | 修复配置/资产路径查找：DLL被加载到 `_storage_` 等子目录、旁边找不到 `DLSS5-AMD` 时，继续到游戏EXE旁查找，避免误读开发目录旧配置。已在《剑星》2560×1440回归前置链，网络内核与权重不变；此修正不解决《生化危机9》同一命令列表中的前置接入限制。包 `OptiScaler-DLSS5-AMD-0.24.1.zip`（385,883,920字节，sha256 1e9ec721…）。 |
| 0.24.2 · [OptiScaler](https://pan.quark.cn/s/f74aaa5c7f9a)（HIP） | 09-19 | 修复addon在无前置任务时仍逐次绘制查配置、锁任务表的CPU开销，并减少日志计数争用；F6关闭直接旁路前置捕获/颜色复制，已捕获任务仍执行一次。《剑星》主城回归约49fps（此前约31fps），同步/异步GPU检查通过。网络内核与权重不变。包 `OptiScaler-DLSS5-AMD-0.24.2.zip`。 同日重打完整包补上FPS/状态显示开关，下载链接已更新。 |
| 0.25 · [Magpie](https://pan.quark.cn/s/09630ed99606) · [OptiScaler](https://pan.quark.cn/s/636691131c5f)（HIP） | 09-19 | **优化**：复用C32/多头注意力的指数计算、简化倒数计算；中间特征和解码输出直接用FP8字节传递，减少数据搬运；解码完整分组走快速路径。**修复/兼容**：修复900档尾部漏写和中文路径加载失败，新增9060/XT的gfx1200内核，与gfx1201自动选择。9070 XT回归通过，9060/XT待实机反馈；Magpie实测1080P只做DLSS5约37fps，与之前基本持平。Magpie、OptiScaler均提供完整包。 |
| 0.26 · [Magpie](https://pan.quark.cn/s/7ce2ca11db43) · [OptiScaler](https://pan.quark.cn/s/c880a70f0824)（HIP） | 09-19 | FFN直接读取FP8字节片段，省去入口共享缓冲暂存及两道同步；C256权重在初始化时预排成连续矩阵片段，减少分散读取和字节拼装。补齐漏打包的R11G11B10解码shader，修复《匹诺曹的谎言》降低效果品质后黑屏，用户复测恢复；增加shader编译/绑定校验。两款完整包已生成，包内文件及44种shader组合校验通过。 |
| 0.26.1 · [OptiScaler-REFramework](https://pan.quark.cn/s/624c87a6aa11)（HIP，非常规版） | 09-20 | **专门针对RE9这类特殊接入场景的非常规版本，普通游戏请用通用版；目前仅《生化9》实测。** 后置HIP兼容：R10G10B10A2/FP16转换，FSR后处理、固定900P计算，保留1080P SDR输出保护；补齐状态/分辨率/Present帧率与F7信息开关。集成REFramework、OptiScaler、ReShade、完整模型及gfx1200/gfx1201内核，沿用0.26优化。用户实玩通过。 |
| 0.27 · [Magpie](https://pan.quark.cn/s/ec3a3282aa76) · [OptiScaler](https://pan.quark.cn/s/004278159ed8) · [OptiScaler-REFramework](https://pan.quark.cn/s/010683548f68)（HIP） | 09-20 | 精确流式ViT注意力减少中间存储与重复读取，保持原计算/舍入；可选R3自适应复用增加变化检测、静止输入延长缓存和融合提交，默认关闭。三包直接使用仓库默认配置，带完整模型和双架构内核，不含INT4/剪枝。REFramework保留固定900P、最高1080P SDR后置契约。DLL重新编译，三包各44个shader变体及ZIP逐文件校验通过。 |
| 0.28 · [Magpie](https://pan.quark.cn/s/11547f398eb4) · [OptiScaler](https://pan.quark.cn/s/f7f423b0ea3a)（HIP） | 09-22 | 六项无损核优化：RGB共用读取、C128/C256零填充跳过、ViT展开/投影及解码投影固定尺寸优化。常规《剑星》实玩效果/帧率基本不变。普通版宿主不变，完整模型和双架构核随包；RE9 0.28下载已撤下，改用下方0.28.1。 |
| 0.28.1 · [OptiScaler-REFramework](https://pan.quark.cn/s/1375693a0d21)（HIP） | 09-22 | RE9专用完整包：真实输入超限时在HIP初始化前拒绝并保留原始超分；初始化失败安全回滚，改回有效尺寸可恢复，保护未退休帧。10组/12提交帧回归和用户初步实玩通过，宿主/runtime需配套更新；源码与TheAutomatic署名随包。 |
| 0.29 · Magpie · OptiScaler · OptiScaler-REFramework（HIP） | 09-23 | 超过1920×1080的输入不再拒绝：缩到1080档跑网络，再按原版codec方式还原到原分辨率（`DLSS5_FIT_LARGE=1`，issue #6；《剑星》2K Native AA 44fps、RE9 Native AA实测；超宽屏未实机）。共享核自0.28以来六项逐位无损优化（栅栏作用域、C32折叠FFN、字节链+向量化输入、注意力寄存器化、in16别名、FFN尾段转置）约−7%，《剑星》900P约60fps。RE9宿主不变、runtime更新。 |

## 权重

网络权重属于 NVIDIA。宿主代码运行时加载的权重文件（`block31-expand.f32`、`post70-attention.f32` 等，连同参考
dump 约 16 GB）不在仓库里，是用 `Development/` 里的脚本（`prepare_native_*_gpu.py` 和各块笔记）从自己拥有的
`nvngx_dlssnr.dll` 提取的；脚本记录了布局，但不是一条整理好的流水线。仓库不分发任何 NVIDIA 的 DLL。

## 作者

Kien——方向、游戏接入、测试。逆向、核与优化由 AI 协作者（Claude、GPT）完成，`Development/` 里的工作
笔记是它们写的。完整过程见[公众号 DLSS5 系列合集](https://mp.weixin.qq.com/mp/appmsgalbum?__biz=MzYzMzMwNzk0NA==&action=getalbum&album_id=4687269655390453762#wechat_redirect)。简历 / Resume：[在这里](https://github.com/lmxxf/ai-theorys-study/blob/main/resume/README.md)。

## 许可

本仓库代码以 MIT 许可发布。NVIDIA 的二进制和权重不在其列。
