# RE9 超分调用顺序观察（2026-09-20）

只观察原始超分执行后的普通draw/dispatch调用，不运行神经网络、不延后FFX、不Close/Reset游戏列表。未覆盖所有间接命令/资源消费者；没有记录到draw不能单独证明可安全前置。

- 游戏：`C:\Program Files (x86)\Steam\steamapps\common\RESIDENT EVIL requiem BIOHAZARD requiem`
- 首版54aa65b6…已安装并启动，PID3212，可见标题菜单及OptiScaler；DLSS输入→FSR4.1.1，约1130×636→1920×1080。loader挂钩成功却没收集到FFX调用。
- 最新观察版SHA256 `2bc1ee441c117c349bd30364789f8e23dc7f61d1354e010622fb227060f944e3`，已编译并放到`D:\DLSSNR-Lab\re9-opti\native-re9-observer.addon64`，00:45已同步安装到root/_storage_并启动，PID32500。
- 新版观察独立upscaler provider，同时钩OptiScaler导出的`NVSDK_NGX_D3D12_EvaluateFeature`出口，记录列表类型和前四条后续命令调用栈；仅前16次调用。
- 用户退出游戏后：远端`install-observer.ps1 -Action Update`同步root和_storage_观察DLL，再用原`optiscaler-re9.ps1 -Action Launch`启动。安装脚本有进程/校验保护。
- 日志：游戏`DLSS5-AMD\logs\re9-ffx-tail.txt`。`after_original_ngx`与`after_original_ffx`之后的调用来源需要分别解释。
- `install-observer.ps1 -Action Restore`在游戏退出后移除观察DLL；旧dlss5-amd.addon64.off保持原样。备份`D:\DLSSNR-Lab\re9-opti\before-observer`。

从仓库根运行`prepare-observer.py`生成`/tmp/re9-observer-build`，再用该目录scripts/build-addon.sh与本仓third_party依赖编译--hip。这里的patch和NATIVE_RE9_OBSERVE_ONLY宏只用于诊断，不是生产接入实现。

## 已读源码线索

OptiScaler 0.9.4（7534ad0）的[FfxApi_Proxy.h](https://github.com/optiscaler/OptiScaler/blob/7534ad0/OptiScaler/proxies/FfxApi_Proxy.h)里，D3D12_Dispatch可直调upscaling_dx12.Dispatch；若后端DLL同时被输入hook使用，函数指针还可能成为Detours trampoline。单钩loader导出不能保证看到内部调用。

[FSR31Feature_Dx12.cpp](https://github.com/optiscaler/OptiScaler/blob/7534ad0/OptiScaler/upscalers/fsr31/FSR31Feature_Dx12.cpp)在FFX返回后还可能记录RCAS、输出缩放、ImGui；因此旧following_work日志需要重新归因，不能直接认定全部来自游戏。NGX观察签名核对[输入实现](https://github.com/optiscaler/OptiScaler/blob/7534ad0/OptiScaler/inputs/NVNGX_DLSS_Dx12.cpp)。

下一步先拿真实调用栈：若只有OptiScaler可选后处理，验证关闭这些功能后的顺序；若游戏仍在同列表消费，则需要新的接入边界/后置路径。HIP读取本帧颜色要求对应D3D12生产命令已提交执行，提前调用CPU函数不会让未提交的GPU命令自动完成。保留following_work检查。

## 00:45 实测结果

NGX出口钩子成功，16次Evaluate返回均为成功、列表类型DIRECT(0)。超分之后同一列表仍有51～53次普通draw/dispatch：51次5帧、52次1帧、53次10帧。调用栈直接指向re9.exe（dispatch路径+5865c16；draw+59098aa；draw_indexed+59099a3），因此即使跳过OptiScaler的可选后处理，游戏仍不满足当前前置的列表尾部契约。provider导出钩子仍未见调用；实际NGX出口已提供独立证据，不据此断言provider不执行。完整数据见results。

后续路线已向用户提出选择：后置兼容模式（先游戏/FSR、再DLSS5，包含UI，继续HIP）或继续找真正前置的引擎提交边界。后置候选须验证Present回调时序并处理R10G10B10A2（当前后缓冲DXGI24，1920×1080；现有NativeIsGameColor尚不接受该格式）。现有HLSL RecordUnsubmitted有单列表device-hang历史保护，不能当作现成修复或直接解除限制。当前运行的是只观察版本，未实现新的DLSS5接入。

## 后置兼容开发（01:36起）

用户已授权助手直接退出/启动RE9继续开发。`present_addon.cpp`是独立后置插件；原观察插件改`.off`，不同时加载。游戏/OptiScaler提交完成后，在ReShade present事件中使用自己的命令列表进行R10→FP16→HIP→R10，UI也受处理；暂限SDR R10、≤1920×1080，900P网络。ReShade 6.8 [on_present源码](https://github.com/crosire/reshade/blob/v6.8.0/source/dxgi/dxgi_swapchain.cpp)确认此事件先于效果渲染；[D3D12 swapchain实现](https://github.com/crosire/reshade/blob/v6.8.0/source/d3d12/d3d12_impl_swapchain.hpp)提供原生IDXGISwapChain3。

`build-present.sh [输出]`编译独立插件，`test_present_bridge.cpp`独立GPU往返校验18组逐位一致。`install-present.ps1`有进程保护与首次备份（before-present），Update只更新DLL；中断安装可Resume。`set-present-mode.ps1 -Mode 0/1/2`为只转换/推理/绕过，运行时每秒读取；F6切换绕过。首次HIP帧前后诊断输出到DLSS5-AMD/logs/re9-present-{before,after}.rgba16f，普通帧不读回。初始化失败/提交失败会停止处理并保留可能在途的资源，不自动循环重试。

初版调用ReShade的resource返回接口崩溃，改为原生DXGI GetBuffer（COM输出参数）；当前游戏验证结果见DevHistory最后一项。此候选尚未进入0.26发布包。

01:58实测：修正后的1d8ac806…已在RE9菜单跑通后置HIP，首帧前后均全有限且输出改变，连续超过2100帧，F6绕过成功。保持1080P输出、900P网络、SDR；菜单30fps上限不作为性能对比，实际游戏质量待用户测试。

## 信息层（07:02起）

右上角显示后置ON/OFF/初始化/失败状态、有效网络尺寸与输出尺寸，第二行显示本插件Present回调频率（不是插帧后的显示器帧率）。900档显示有效1600×900，内部补齐到960行不作为画面分辨率。F6切换处理；F7在本次运行中隐藏/恢复全部信息。`DLSS5_SHOW_FPS=0`关闭帧率行，`DLSS5_NOTICE=0`关闭状态/尺寸行，两项每秒热读，均为0时不绘制。初始化期间也有提示；HDR绕过时不往HDR画面画SDR文字。

信息在推理/写回完成后用独立列表绘制；NativeTextOverlay增加RGB10A2输出模式，其他格式分支不变。必须连同新版native_text_overlay.hlsl部署，`install-info.ps1`会备份旧DLL/字体shader/配置、更新并开启两行。首帧诊断读回默认关闭，需要时在flags中设置`DLSS5_RE9_SNAPSHOT=1`。测试后再制作独立0.26 OptiScaler-REFramework包，本轮不重打通用包。
