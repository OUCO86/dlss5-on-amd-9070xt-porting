# RE9 超分调用顺序观察（2026-09-20）

只观察原始超分执行后的普通draw/dispatch调用，不运行神经网络、不延后FFX、不Close/Reset游戏列表。未覆盖所有间接命令/资源消费者；没有记录到draw不能单独证明可安全前置。

- 游戏：`C:\Program Files (x86)\Steam\steamapps\common\RESIDENT EVIL requiem BIOHAZARD requiem`
- 首版54aa65b6…已安装并启动，PID3212，可见标题菜单及OptiScaler；DLSS输入→FSR4.1.1，约1130×636→1920×1080。loader挂钩成功却没收集到FFX调用。
- 最新观察版SHA256 `2bc1ee441c117c349bd30364789f8e23dc7f61d1354e010622fb227060f944e3`，已编译并放到`D:\DLSSNR-Lab\re9-opti\native-re9-observer.addon64`，尚未换入游戏。
- 新版观察独立upscaler provider，同时钩OptiScaler导出的`NVSDK_NGX_D3D12_EvaluateFeature`出口，记录列表类型和前四条后续命令调用栈；仅前16次调用。
- 用户退出游戏后：远端`install-observer.ps1 -Action Update`同步root和_storage_观察DLL，再用原`optiscaler-re9.ps1 -Action Launch`启动。安装脚本有进程/校验保护。
- 日志：游戏`DLSS5-AMD\logs\re9-ffx-tail.txt`。`after_original_ngx`与`after_original_ffx`之后的调用来源需要分别解释。
- `install-observer.ps1 -Action Restore`在游戏退出后移除观察DLL；旧dlss5-amd.addon64.off保持原样。备份`D:\DLSSNR-Lab\re9-opti\before-observer`。

从仓库根运行`prepare-observer.py`生成`/tmp/re9-observer-build`，再用该目录scripts/build-addon.sh与本仓third_party依赖编译--hip。这里的patch和NATIVE_RE9_OBSERVE_ONLY宏只用于诊断，不是生产接入实现。

## 已读源码线索

OptiScaler 0.9.4（7534ad0）的[FfxApi_Proxy.h](https://github.com/optiscaler/OptiScaler/blob/7534ad0/OptiScaler/proxies/FfxApi_Proxy.h)里，D3D12_Dispatch可直调upscaling_dx12.Dispatch；若后端DLL同时被输入hook使用，函数指针还可能成为Detours trampoline。单钩loader导出不能保证看到内部调用。

[FSR31Feature_Dx12.cpp](https://github.com/optiscaler/OptiScaler/blob/7534ad0/OptiScaler/upscalers/fsr31/FSR31Feature_Dx12.cpp)在FFX返回后还可能记录RCAS、输出缩放、ImGui；因此旧following_work日志需要重新归因，不能直接认定全部来自游戏。NGX观察签名核对[输入实现](https://github.com/optiscaler/OptiScaler/blob/7534ad0/OptiScaler/inputs/NVNGX_DLSS_Dx12.cpp)。

下一步先拿真实调用栈：若只有OptiScaler可选后处理，验证关闭这些功能后的顺序；若游戏仍在同列表消费，则需要新的接入边界/后置路径。HIP读取本帧颜色要求对应D3D12生产命令已提交执行，提前调用CPU函数不会让未提交的GPU命令自动完成。保留following_work检查。
