# RE9 前置颜色调查（2026-09-22 07:30）

用户实测：ColourStrength=1明显褪色；F6关闭NR大体恢复、尚有少量白；ColourStrength=0后NR几乎只剩明暗。后者符合decode的 `lerp(original*ratio, upgraded, ColorStrength)`，不能作为根因修复。

重新核对 https://github.com/TheAutomatic/dlss-5-amd-project/tree/release/1.9.0 ，远端HEAD仍8f71f73bfc836a37936e7cee6701750ad4e8bfec，使用git show读取未打补丁源码：

- AmdBridge.cpp取得ExposureTexture、DLSS_Pre_Exposure、DLSS_Exposure_Scale。
- Daniel路径AmdPreSr.cpp的ExposureShader计算texture.r * exposureScale / preExposure，交给该后端；ColorEncoding.h提供显式linear/sRGB/gamma2.2转换，不自动证明RE9是哪种。
- 通用DlssNr_Dx12.cpp及precompile/dlssnr.hlsl有基于游戏曝光的WhitePoint、输入归一化及输出还原；AMD路径在此之前return，不能认为这些选项也作用于lmxxf。
- lmxxf的LmxxfNrFrameInfo没有曝光纹理、预曝光、曝光scale字段；RecordInputs/Outputs都固定传1.f，AmdEncoding亦未在该后端使用。此是上游lmxxf初接入就存在的缺口，我们沿用了。
- 上游lmxxf同样使用我们的codec合成公式，不存在可直接复制的已验证RE9色彩修复。菜单强度范围还宽于我们codec的0..1契约，后续需收紧。

下一步：恢复全强度的测试候选前，先抓RE9真实入口、编码proxy、神经输出以及原始曝光值；做TransferStrength=0的FP16旁路对照隔离格式/FSR输入替换；确认实际RGB范围与曝光意义，再把曝光参数贯通ABI，并在GPU上对同帧曝光进行归一化/还原。检验亮暗场景与proxy饱和比例，不能单靠调饱和度或固定曝光补偿掩盖。预曝光和曝光scale曾在启动诊断均为1，但未读曝光纹理的值，不足以排除曝光问题。当前不认定全部褪色来自曝光；模型本身的色度变动仍需对照。

本轮只审计，未再次修改运行中的游戏配置/DLL。


## 实际抓取与修复（07:37–07:43）

原候选同帧抓取239587750：输入RGB9E5 1506×848，中位通道值1.457、P90=5.3125、max708；曝光纹理R16F=0.044189453125，preExposure/exposureScale均1。旧codec写死白点1导致proxy三通道均>0.98的像素58.66%，neural59.52%。曝光归一化缺失是已观测的问题，不能只称画面主观不同。

修复可选GPU曝光SRV t4：编码/解码同帧读取1×1 R16F/R32F曝光，归一化为 input * exposure * exposureScale / preExposure，输出逆变换。无曝光调用保持原行为；参数/纹理校验、设备核对和资源引用保留。宿主/runtime实验ABI升2并严格检查结构大小，避免旧宿主与新runtime错配。曝光资源换指针时保守drain并重建链；若游戏频繁轮换，会有额外成本，后续观察。

合成RGB9E5(.25,.5,.75)和32倍输入/1/32曝光对照：proxy、neural逐位同；最终RGB精确32倍，alpha同。旧路径24次逐字节比较均diff0，12次debug视图检查通过（1080FP16、FIT FP16、FIT UNORM8/sRGB）。抓取工具只在capture-colour.request存在时录制readback，并在提交确认+GPU完成后写文件，无持续每帧CPU回读曝光。

部署备份D:\DLSSNR-Lab\re9-presr\backups\exposure-20260922-074316；runtime A229D50B2E4DA8AF80CF321F8130C2E24AAE95001BEA48FD7C6D0FD163C99783。恢复TransferStrength=ColourStrength=1，继续游戏验证。


修复后游戏capture240239156：同曝光0.044189453125，proxy中位0.3059，三通道>0.98占0.08535%，neural0.04319%；亮度/色度有有效变化（完整强度），没有旧版大片饱和。前后为不同菜单帧，不作像素对齐A/B；受控验证来自32倍输入/曝光逆缩放测试。

初期两次启动卡在首个HIP enqueue，增加追踪后第三次成功。源码发现权重首次Upload会hipStreamSynchronize；新增显式PrepareStagedKernels在挂外部producer wait前用零输入完成权重/核准备，只供RE9调用。准备前后6个完整proxy/neural/result读回缓冲逐字节相同。最终去掉高频trace，runtime F5CF76979D1753CE3E4498F85A45046B984CA8B0E54C80F17A41C45481E7CB68，备份exposure-20260922-075132；第一轮重启已验证完整强度前5帧均正常。不能把启动偶发问题归因为已完全证明的曝光资源同步错误。
