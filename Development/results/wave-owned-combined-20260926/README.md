# 单wave窗口候选组合实测

## 2026-09-26：prefix/post完整单wave与MH组合，整网耗时下降6.0%/6.6%

C32加入post70和prefix0，完整10块：post保留低分辨率特征+FP8 skip合并的两次Hrtz、最后RGB32项顺序f32点积；prefix复用生产噪声/历史特征，用低16lane算特征、高16lane取后8项，保留两次FP16 WMMA（零K片段也保留），main8和下采样顺序不变。两端分别176/174VGPR、零spill、4KiB LDS。完整C32模块73a2dfdb…，两档三组200帧ABBA逐位：900 −0.29543ms、1080 −0.45633ms。

新增DynamicFrames，按fixture生成位移/增益/黑白输入、seed=123+17*f，首帧null history、后续前一帧输入作history。每帧先baseline后candidate，同步完成后比最终RGB；两档各16帧完整C32全逐位。它证明Network入口的数学/历史输入一致，不替代NativeGameFrame完整宿主生命周期。

wave-owned-combined生成host把C32和MH候选接到同一Network，mode0 prod8、1 MH36块、2 C3210块、3合用46块。MH模块cc8166b3…（C64/C128整块融合+C256 attention-only，非DirectFeature），C32模块73a2dfdb…。两档三组200帧ABBA：900配对−0.70055/−0.70633/−0.70033ms，均−0.702405ms，11.661035→10.958630ms，耗时−6.0235%；1080−1.10831/−1.10106/−1.09592ms，均−1.1017625ms，16.693508→15.591746ms，耗时−6.5999%。全部槽首尾逐位、46块/帧计数正确；组合也完成两档各16帧动态历史对照，全逐位。

所有source生成器、原始日志/CSV、module manifest与校验脚本归档。未部署、未宣称游戏FPS提高相同比例。下一步可选生产集成、gfx1200编译、NativeGameFrame完整回归，再测真实游戏；后续继续研究ViT/C512/布局。6.6%是阶段结果，尚未实现用户要求的质变，也未证明Daniel42%的精确贡献分配。
