# Daniel 闭源 v0.4.0 剑星实机对照（2026-09-26）

同机（9070 XT，驱动 32.0.31007.2048）、同场景、《剑星》2K 质量档（渲染 1707×961 → 2560×1440）。
切换方式 `swap.ps1`：我们整套只经 `dxgi.dll`（OptiScaler）拉起，改名为 `dxgi.dll.ours-optiscaler` 后放入 Daniel 的 mod DLL（`d62be3d8…`，即 v0.4.0 安装包内 DLL）为 `dxgi.dll`，加 `nvngx_dlssnr.dll`（`e16bcf15…`）和安装包默认 ini。未运行其 GUI 安装器。游戏内超分选 FSR（其钩子挂游戏自带 FFX，FSR 4.1.1）。测完已切回（dxgi `fbfb6676…`）。

| | Daniel 0.4.0 | 我们 wave-owned |
|---|---|---|
| 用户读 FPS | 56～57 | 49～50（prod8 47～48） |
| 网络输入 | 渲染分辨率 1707×961 原样（色彩纹理 1708×964 裁到渲染尺寸） | FIT 到 1080 档，处理区 1920×1152 |
| 像素 | 1.64M | 2.21M（+35%） |
| 网络 GPU 时间 | 11.7～12.2ms（日志 200 帧均值） | 离线 15.87ms |

按像素折算我们约 11.8ms，与其持平：**差距来自网络尺寸，不是内核效率。** 0.3.3→0.4.0 的 42% 是其自身旧通用路径（每窗口 global workspace）的补课。

画质侧（粉丝反馈"浅"）的日志依据：`history off`（默认 PreHistory=0，时序历史未进网络）、默认 LocalTone=0、网络在 961 行而非 1080 层。另：inline 模式，游戏队列自旋等网络（spin 12.2ms）。

原始日志 `stellar-2k-quality.log`。
