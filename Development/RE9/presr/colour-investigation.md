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
