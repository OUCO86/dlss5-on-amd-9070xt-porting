# 单wave窗口候选组合实测

## 2026-09-26：prefix/post完整单wave与MH组合，整网耗时下降6.0%/6.6%

C32加入post70和prefix0，完整10块：post保留低分辨率特征+FP8 skip合并的两次Hrtz、最后RGB32项顺序f32点积；prefix复用生产噪声/历史特征，用低16lane算特征、高16lane取后8项，保留两次FP16 WMMA（零K片段也保留），main8和下采样顺序不变。两端分别176/174VGPR、零spill、4KiB LDS。完整C32模块73a2dfdb…，两档三组200帧ABBA逐位：900 −0.29543ms、1080 −0.45633ms。

新增DynamicFrames，按fixture生成位移/增益/黑白输入、seed=123+17*f，首帧null history、后续前一帧输入作history。每帧先baseline后candidate，同步完成后比最终RGB；两档各16帧完整C32全逐位。它证明Network入口的数学/历史输入一致，不替代NativeGameFrame完整宿主生命周期。

wave-owned-combined生成host把C32和MH候选接到同一Network，mode0 prod8、1 MH36块、2 C3210块、3合用46块。MH模块cc8166b3…（C64/C128整块融合+C256 attention-only，非DirectFeature），C32模块73a2dfdb…。两档三组200帧ABBA：900配对−0.70055/−0.70633/−0.70033ms，均−0.702405ms，11.661035→10.958630ms，耗时−6.0235%；1080−1.10831/−1.10106/−1.09592ms，均−1.1017625ms，16.693508→15.591746ms，耗时−6.5999%。全部槽首尾逐位、46块/帧计数正确；组合也完成两档各16帧动态历史对照，全逐位。

所有source生成器、原始日志/CSV、module manifest与校验脚本归档。未部署、未宣称游戏FPS提高相同比例。下一步可选生产集成、gfx1200编译、NativeGameFrame完整回归，再测真实游戏；后续继续研究ViT/C512/布局。6.6%是阶段结果，尚未实现用户要求的质变，也未证明Daniel42%的精确贡献分配。

## 2026-09-26：完整NativeGameFrame回归与gfx1200编译通过，6.7%收益保留

prepare-runtime.py把已验证组合Network接进原NativeGameFrame/D3D12桥接与benchmark_vit_reuse.cpp，仅以进程flag DLSS5_HIP_WAVE_OWNED=0/1选择基线/候选，记录销毁时46块/帧的累计调用/替换数。尚未改生产头文件、游戏或发布包。gfx1200两额外模块用gfx1201同一源构建通过，完整module hash清单归档；没有gfx1200硬件运行证据。

900/1080静态与移动、720移动、900连续历史，共6对12帧。72个候选RGBA16F帧逐帧SHA256与基线相同，所有已检查帧无非有限值，累计替换数与实际帧数吻合。覆盖真实捕获HDR输入→D3D12 encode→HIP网络→history/decode→D3D12输出，补上前轮仅Network接口的缺口；不覆盖所有游戏宿主资源生命周期。

完整处理长测每槽1000帧，去前200帧，按基线/候选/候选/基线：900四槽11.94554/11.23668/11.28361/12.00644ms，均值11.97599→11.26015，−0.71585ms/−5.98%；1080四槽16.98308/15.85462/15.87311/17.01188ms，均值16.99748→15.86386，−1.13362ms/−6.67%。计时槽只检查抽样输出，不能称8000帧全部逐位；72帧正确性回归单独逐帧比较。

所有帧hash、flags、原始日志与CSV、校验脚本、host输入头文件hash归档wave-owned-combined。下一步生产可选路径集成、兼容条件/回落、双架构打包与游戏计时；继续研究Daniel新增ViT/C512寄存器路线，目标仍未完成。
