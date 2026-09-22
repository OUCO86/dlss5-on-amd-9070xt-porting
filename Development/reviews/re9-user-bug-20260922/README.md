# RE9 网友启动故障：2026-09-22 离线日志调查

## 结论

“没有效果”的直接原因已经定位：runtime 在创建 codec 的 D3D12 compute pipeline state 时返回 `0x80004005`（E_FAIL），每帧 PrepareFrame 失败，因此没有可提交的 NR job。不是根据显示分辨率猜测输入超限。底层为什么拒绝 PSO，现有日志不足以确定；不能把它直接解释成 HIP 死锁、曝光错误或驱动版本问题。

原始日志只留在工作区 `temp/bug20260922`，本报告不复制网友个人路径和完整日志。未操作游戏、未远程 GPU 测试、未部署、未打包；仅归档调查报告。

## 已确认事实与证据

- `OptiScaler.log:1`：`8f71f73_lmxxf_staged / 20260922_RE9_PreSR`，已加载本项目特殊宿主；`:16-24` 显示 nofg、RunBeforeSR=true、lmxxf backend、诊断 off、强度均为 1。
- `OptiScaler.log:203-218`：存在 RX 9070 XT 和 Arc A770；记录到 D3D12 设备创建使用 9070 XT。没有证据支持“选错 Intel 卡”。
- `re2_framework_log.txt:95-97`：启动时 runtime 从游戏根目录复制到 `_storage_`；`:2614-2615` 明确记录加载的是游戏根目录 runtime。没有 DLL 实体和 SHA256，因此不能证明正好等于发布包二进制；现有证据不支持先归咎 `_storage_` 旧 runtime。
- `OptiScaler.log:600-604`：找到包内 HIP 目录，modules_ok=48、weights=1、session ready。LMXXF_WEIGHTS_DIR unset 警告本身不是缺权重结论。
- `OptiScaler.log:605`：第一次实际失败为 `PrepareFrame rc=5 handle=false out=false err=codec pso HRESULT=2147500037 1280x544`。`:1024` 在 960×544 同错；`:1817` 最后仍在 1136×640 同错，累计 fail#24991。覆盖数分钟，并非卡住首次 enqueue 的旧症状。
- `OptiScaler.log:511,563,991,1182`：依次出现 1720×720→3440×1440、1280×544→2560×1080、960×544→1920×1080、1136×640→1920×1080。有真正超宽输出，也有 16:9 输出；实际报错输入都在 1920×1080 上限内。
- 日志没有 NR enqueue 成功、device removed、TDR 或异常堆栈。REFramework 日志末尾仍是用户切换菜单/保存配置，OptiScaler 继续报错。不能从这一组日志建立“21:9直接死机”的独立因果链；需要标明对应重现的单独日志。

## 源码对照

`src/native_game_codec.h:90` 在 shader 编译成功后调用 `NativeCreateComputePipelineState`，并生成唯一的 `codec pso HRESULT=...` 错误。`src/native_pso.h:11-12` 只是直接调用设备 CreateComputePipelineState。当前错误文本无法区分 encoder 还是 decoder。

当前本地适配后的 runtime `LmxxfNrRuntime.cpp:605-640` 先执行 bridge Create/PrepareStagedKernels，再创建 encoder、RGB 输入/输出、decoder。因此可以说“没有进入本帧 producer/HIP enqueue/consumer”，不能说“HIP 从未运行过”。若网友 runtime 等于当前发布版本，HIP 预热已跨过。

codec 在 PSO 前已经检查输入几何/格式、曝光纹理（若提供）的 1×1 R16F/R32F、所属设备并创建 root signature。故当前错误不是这些明确的检查拒绝；但日志未记录实际曝光格式、纹理指针和 shader 路径，不能补编这些值。

Shader 源码/缓存错配与 D3D12 驱动或 hook 拒绝均仍可能。`src/native_shader_cache.h` 对磁盘缓存读回没有 DXBC 校验，并会在进程内缓存同一字节；坏缓存可持续导致 PSO 失败，不过目前没有网友缓存实体证明它坏了。缓存 key 含源码与宏，因此正常的源码升级不应自行命中旧版本。

## 额外确认的诊断缺陷

`Development/tools/package-028.ps1:54` 正确移除特殊包不使用的 native-game-flags.txt；但 `src/native_lab_paths.h` 的 NativeLabRoot 仍以该文件存在作为包目录识别条件，找不到就回落作者机器的 D 盘路径。codec step 日志用它（`native_game_codec.h:32`），会在网友机器无声丢失。网友 DLSS5-AMD 日志目录只剩 README 与此一致。此缺陷解释诊断缺失，不解释 PSO 本身失败。

最小修复建议：NativeLabRoot 增加 native-game-tiled-assets 目录作为有效包目录标志，保留原 flags 识别；在 DLL 目录及 exe 目录两种布局验证，别创建无效旧 flags 充当开关。

## 下一步（按信息增益排序）

1. 收集根目录与 `_storage_` 的宿主/runtime SHA256、两个 codec HLSL SHA256、RX9070XT 驱动版本；确认本日志是哪个操作步骤，另取 21:9 卡死那次完整日志。保留 shader-cache 后，以 `DLSS5_SHADER_DISK_CACHE=0` 启动一次对照（新进程才有效）。不应先删全部模组或改 GPU。
2. 小型诊断 runtime：PSO 错误附 encoder/decoder、shader绝对路径与字节码 hash/长度、输入/曝光描述、实际 adapter LUID、GetDeviceRemovedReason；若 debug layer 可用，记录该次创建的 info queue。初始化永久失败应按资源/设置代次停止每帧重建，避免当前数万次重试掩盖首因。
3. 离线 codec harness 使用**网友实际文件**验证 1280×544、960×544、1136×640，RGB9E5、曝光开/关与 1×1 R16F/R32F；先只创建 encoder/decoder PSO，再跑 producer/HIP/consumer。在同型号卡先验证，再交网友测试；只在其驱动失败才进一步定位驱动兼容性。

置信度：失败阶段与“不产生 NR 效果”因果高；底层 PSO 拒绝原因未定。当前无需大范围改渲染同步和超宽几何。

## 用户后续反馈（12:57）

网友重新下载并覆盖后恢复正常，用户决定停止排查。没有旧文件/新文件哈希对照，因此不反推究竟是DLL、shader还是缓存；PSO失败点保留为历史证据，诊断路径缺陷仍是独立发现。

## 追加：真实超限输入后无法恢复（离线 GPU 已复现）

用户补充“启动显示2560×1080，改回也不恢复”。**显示2560×1080本身仍不是输入超限**：网友本日志 `:563` 明确对应输入1280×544。首错仍是 codec PSO，不是下面新复现的 geometry/capacity 错误。

但代码确实还有一个独立恢复缺陷，现已用真实0.28发布runtime在9070上复现：fresh→1280×544、fresh→960×544的 PrepareFrame/RecordInputs 都成功；同一session先送入**实际2560×1080纹理**，得到 `codec unverified input format/geometry`，随后两种有效输入的 PrepareFrame成功，但 RecordInputs均报 `bridge input capacity`。原始结果与harness见 `Development/RE9/presr/tests/resize-recovery/`。

机制（适配后的上游 LmxxfNrRuntime.cpp）：

1. `:562-580` 在检查真实颜色纹理前选网络档位并创建/预热bridge。2560×1080选1080档。
2. `:589-593` 的geoChanged受 `session->encode` 限制。
3. `:634` encoder Create才经 `native_game_codec.h:58` 拒绝超限纹理；`:654-663`异常只删除局部codec对象，保留session bridge/hipPrepared，encode仍为空。
4. 下帧较小输入更新全局geometry到720，但空encode令geoChanged为false；已有1080 bridge被复用，新720 codec建立成功。
5. `:738` RecordInputCopy经 `Development/HIP/hip_d3d12_bridge.h:29` 发现720输入缓冲小于1080 bridge容量，报 `bridge input capacity`。

**修复应分两层**：在任何全局geometry变化/HIP分配前，读取并验证真实纹理尺寸、格式、维度以及FrameInfo尺寸一致性，超限无副作用返回；另外把bridge+codec初始化视作事务，codec失败时在确认尚无提交/等待安全后清理整条新链（包括hipPrepared），或单独保存bridge自身geometry并独立于encode判断是否重建。只加前置超限检查还不能处理合法输入上的PSO初始化异常后换档。

GPU测试前已检查游戏/Magpie退出；仅新增lab测试EXE，使用发布包原始runtime/model/shader，测试进程禁用磁盘shader缓存。无游戏启动/停止、无发布包修改、无全局环境或硬件设置变更。此测试仅到命令录制阶段，不提交producer/consumer；HIP预热会执行。四次GetDeviceRemovedReason均为S_OK。这确认恢复缺陷，不证明网友首错由它触发。

## 追加：“失败后再也起不来”的进程边界

完成上述失败序列后，**不替换任何DLL/资产**再启动两个独立新进程测试1280×544、960×544，PrepareFrame和RecordInputs全部恢复成功，设备正常；见 `tests/resize-recovery/fresh-after-failure.txt`。同样禁用磁盘shader缓存。因此已证明的geometry恢复bug是session/进程内状态问题，不能解释完全退出游戏后的持续失败。用户尚未明确“再也”是否包含确认进程退出后的重启，不应替他补这个前提。

局部源码审计未见runtime将geometry/hipPrepared/失败标志写入磁盘或注册表；网络geometry是进程内static，runtime设置环境变量也是进程局部。没有发现“超限一次永久写坏分辨率状态”的runtime路径。宿主/游戏本身的设置持久化不在这条证明范围内。

另有可跨进程持续的**潜在**缓存缺陷：`src/native_shader_cache.h:69-72` 接受任何长度大于0且可读完的文件，无DXBC结构/hash验证即返回编译成功并加入内存缓存；`:84` 直接截断写目标文件，无临时文件原子替换或写入完成校验。崩溃/中断/多进程读写留下非零截断文件时，下次可能持续PSO失败；PSO失败路径也不会清除此缓存或自动重编。缓存key含源码、entry和宏，故换分辨率但仍同FIT/EXPOSURE变体时仍可命中同一坏文件。此为代码层面的恢复风险，**没有网友缓存文件，尚未证明是本次原因**。收其shader-cache后做禁缓存新进程对照比直接要求重装驱动更有辨别力。

## 修复完成：前置拒绝与初始化事务回滚

修复已落实 `Development/RE9/presr/prepare-host.py` 与生成的 `LmxxfNrRuntime.cpp.patch`、`LmxxfBackend.cpp.patch`，没有只改临时checkout。

- 先读取真实颜色纹理描述，核对上限1920×1080、API尺寸一致性、纹理维度/格式，再允许改变网络geometry或分配/预热HIP。超限返回INVALID_ARGUMENT、空job/output，错误明确打印实际render input与上限。
- 新bridge创建/预热与codec初始化进入同一事务；异常时等待bridge已提交工作安全完成，再清理整个新链与hipPrepared。无法安全等待时保留资源、封锁该session重试，避免释放GPU仍可能引用的内存。
- 尚未Retire的旧帧禁止新有效帧覆盖。正常重建仍走原有GPU drain。超限请求不销毁旧链，返回有效尺寸可继续用原session。
- 宿主不再把INVALID_ARGUMENT当作“geometry/rebind”故障而强制Destroy session；Record失败返回nullptr。原上游 `AmdBridge.cpp:449-454` 只有非空replacement才替换NGX Color，因此继续使用游戏原始输入进行SR。这里保留TheAutomatic原宿主设计贡献；本次是其架构上的边界与恢复适配，不重写提交设计。

候选runtime SHA256 `1b51069c38095988f17403366ac09c1c2e047b28423c7385e669023cf42fbacf`，宿主 `0ef102295a759b51c0c7cba6b8eedb455e9759f5a2b7f9b96309e030c6cd0035`，构建均完成。产物仅在lab resize-candidate目录，未部署/发布/替换0.28包。

独立GPU回归共10组、12个真实提交帧：fresh、超限→有效、有效→超限→有效、合法1080输入注入PSO失败→720档恢复，以及旧帧已录制未提交时拒绝新请求后完成旧帧。两种有效尺寸1280×544/960×544全部通过producer→HIP→consumer→Retire→fence完成；读回RGB半浮点全有限且非零，每种尺寸的所有恢复输出hash与fresh完全相同，无设备移除。PSO注入用独立lab shader的寄存器绑定冲突，返回E_INVALIDARG，**不是重现网友原始E_FAIL**。实际游戏中的FSR继续运行属于已核实宿主分支行为，本轮没有启动游戏作场景验证。

本轮未修改诊断路径与shader磁盘缓存，也没有宣称解决未知PSO E_FAIL或证明网友“原生超限死机”的全部链路。证据与完整测试见 `tests/resize-recovery/submit-results.txt`、`live-frame-results.txt`、`host-build.txt`。
