# 900p内部计算实验

外层仓库和DLSS5子仓库均在`900P`分支；从720p的`dba82fd`继续，main/0.15发布包/tag不变。

## 720p实玩反馈（2026-09-13 23:54）

Zero：《鬼武者》游戏720p（游戏内也开FSR）→DLSS5→2K→XeSS帧生成，基本仍60/30帧，GPU占用95%以上，感觉稍稳。日志确认实际输入和网络均1280×720，持续33.3～33.4ms/帧；不是720开关没生效。没有把独立测试台约91fps冒充游戏帧率，也未据此断定单一限速原因。

## 900p实现（2026-09-14）

新参数`DLSS5_NETWORK_HEIGHT=900`，支持720/900/1080，优先于兼容的`DLSS5_NETWORK_720P`。缺省仍1080；旧720flag继续有效。

有效1600×900，处理1600×1024；编码器网格800×512、400×256、200×128、100×64、50×32，head为25×16，ViT400个真实token。900分辨率只新增明确的50×32 split/head合同，未笼统放宽任意尺寸；位移pack/crop/stream索引逐像素验证四种shift，head2×2池化覆盖全部像素，400-token映射双射。QKV和FFN沿用修好的m1 tiled核，FP8注意力尾块沿用720的mask。decoder400/1600/6400/25600/102400 token对应宽25/50/100/200/400。

CPU几何、参数优先级测试及插件/测试台交叉编译通过，207个shader编译通过。为避免复制整份权重，隔离测试复用`D:\DLSSNR-Lab\network-720p\DLSS5-AMD\native-game-tiled-assets`（已更新成兼容三档的实验shader），900测试exe/flags/日志在`D:\DLSSNR-Lab\network-900p\`，不使用正式游戏资产。

## 测量

固定合成梯度/棋盘源，零运动向量，时序开启，3帧预热后60帧；计时含encode/网络/时序/decode及队列提交间隙，不含游戏/Magpie/FSR4/FG/输入恢复。

| 内部尺寸 | 平均GPU耗时 | 中位 | 最短 | 平均对应FPS | 最短帧对应FPS |
|---|---:|---:|---:|---:|---:|
| 1600×900 | 16.708ms | 16.680ms | 16.552ms | 59.85 | 60.41 |

CPU墙钟平均16.889ms。5,760,000个历史float全部有限；RGB范围20～226、均值128.526，输出图已查看，梯度和棋盘结构正常。这是独立推理数据，900p实际游戏表现待Zero测试。

本地结果`release/900p/900-a.log/.csv/.png`；benchmark沿用`Development/720p/benchmark_frame.cpp`，新增900参数，不复制另一份源码。

## Magpie部署

按Zero要求切900p：DLL SHA256 `72F87A97BFB3AD5D0EFD3FF11DA56B8FBFB778478BE2DF908E30E43CDCE15FD2`，DLL+13个配套shader文件部署并逐项hash核对，flags清除旧720条目、加入`DLSS5_NETWORK_HEIGHT=900`。Magpie已重启；FSR4/FG等效果组设置不改。游戏窗口可选1600×900以对比完整900输入。

备份`D:\DLSSNR-Lab\network-900p\before-magpie-900p\`，回退到此前720安装：`D:\DLSSNR-Lab\network-900p\deploy.ps1 -Action Restore`。部署/回退会先关闭Magpie；包含DLL、shader、manifest和flags，不碰游戏文件。更早0.15备份仍在network-720p/before-magpie-720p。

## 0.15-900P整包（2026-09-14）

Zero实玩确认900p效果比720p更好、帧率还算稳定，1080p加插帧则不稳，要求打0.15-900P。固定900，不做自适应。

包`D:\DLSSNR-Lab\Magpie-DLSS5-AMD-0.15-900P.zip`，358,038,890字节，SHA256 `718d77941674d6e851e7babc14b40a596da52e86aec603f44f956b99ff6811d5`；同路径`.zip.sha256`。676个文件逐个解压hash校验通过。DLL仍为刚实玩的`72F87A97…`，包含全部匹配的900p预编译及运行时shader；flags默认900、光流1/0/0、FSR4充满屏幕、XeSS FG开启。原0.15包保留。尚待Zero上传后补下载链接。

2026-09-14 00:25：整包已上传，下载 https://pan.quark.cn/s/a5339e4c8549 。

## 2026-09-14 07:42：《剑星》游戏内接入

按Zero要求，游戏退出后部署900p DLL到Steam《剑星》`SB\Binaries\Win64\native-submission-order.addon64`，继续使用该目录既有ReShade `d3d12.dll`与Agility721。游戏目录无本地DLSS5-AMD遮蔽，资产/flags仍读`D:\DLSSNR-Lab`。DLL+40个shader文件逐项hash校验通过；游戏FFX库导出ffxDispatch/ffxDestroyContext检查通过，驱动仍32.0.31007.2048。

游戏参数：`DLSS5_NETWORK_HEIGHT=900`、`DLSS5_FIT_INPUT=1`、`DLSS5_CODEC_SRGB=0`、`DLSS5_SHOW_FPS=1`；使用原生引擎运动向量和时序。去掉旧DEBUG_DUMPS/BLACK_PROBE/GAME_PROBE/DEBUG_TINT/RESERVE_VRAM_MB，保留其余游戏参数。`scripts/game-flags.txt`与`Development/900p/game-flags.txt`记录该配置。

备份`D:\DLSSNR-Lab\network-900p\before-stellarblade-900p`，回退同目录上一级`deploy-stellarblade.ps1 -Action Restore`（要求游戏退出）。保留原Magpie安装和发布包。尚未启动游戏验画面；游戏内开启FSR触发网络，使用游戏内钩子时保持Magpie关闭。
