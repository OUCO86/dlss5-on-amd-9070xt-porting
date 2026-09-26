
## 2026-09-26：C32完整窗口单wave链式原型逐位跑通

独立额外模块c32-wave1替换block2/3/67/68四个非finish chain。保留输入输出窗口FP8、shift/crop补零、三段残差对角、C32专用FP16平方和与四个K16顺序softmax归约。Q/K/V寄存器驻留，FFN展开转置直接收缩，AV直送projection；4KiB LDS只存FFN半精度残差，单wave无需组barrier。

首版两档各三组200帧ABBA、每槽首尾RGB逐位同，每帧4次替换计数正确：900 −0.05340ms、1080 −0.08415ms。VGPR240、零spill，module380a5da9…；收益仅约0.5%，不当成目标完成。跨tile地址隔离版本239VGPR、零spill，1080 −0.06430ms（同样三组逐位）；没有实测改善。FFN隐藏片段滚动循环对照也完成1080三组逐位：−0.10293ms，VGPR仍240，module efc870c3…；与首版差仅约0.019ms且跨批，不据此断言额外提升。后续优先扩大到mapped/finish，再查prefix/post布局。未改生产/部署，多头组合与完整历史回归尚待。

## 2026-09-26：C32扩到八块；滚动窗口降寄存器并扩大收益

mapped首块block1/66和finish block4/69加入单wave原型，分别保留mode0输入先转half再乘scale、裁切/F转化和2×2下采样原求和顺序。finish用原4KiB半精度残差平面复用输出，未增加全局临时缓冲。八块首版两档三组200帧ABBA逐位，900 −0.09231ms、1080 −0.13849ms；mapped256VGPR/private60B/14spill，chain240、finish244VGPR。

QKV子段坐标隔离+编译调度栅栏未降压力（chain246、mapped15spill），1080短筛−0.06934ms；单wave改WGP mode短筛−0.11416ms，均无改善证据。保留开关默认关。

关键变化是保留窗口四tile外层循环：Q/K/V从动态C++数组换为可统一索引ext_vector，避免全展开与数组溢出。RollHidden+RollWindow：chain/mapped165VGPR、finish174VGPR、全部零spill、4KiB LDS；模块e51696a7…。两档三组200帧ABBA，900配对−0.16490/−0.18124/−0.17031ms（均−0.17215），1080−0.24577/−0.26211/−0.26295ms（均−0.25694），所有槽首尾逐位、8块/帧计数正确。不能把跨批差额精确归因于一个编译设置，但资源变化和整网增益方向一致。

未部署，尚未与MH候选组合、未跑完整多帧历史。下一步prefix/post全分辨率两端，随后组合回归。C32旧版Daniel已有，不当成0.3→0.4新增原因；当前结果仍远未到质变目标。

## 2026-09-26：prefix/post完整单wave与MH组合，整网耗时下降6.0%/6.6%

C32加入post70和prefix0，完整10块：post保留低分辨率特征+FP8 skip合并的两次Hrtz、最后RGB32项顺序f32点积；prefix复用生产噪声/历史特征，用低16lane算特征、高16lane取后8项，保留两次FP16 WMMA（零K片段也保留），main8和下采样顺序不变。两端分别176/174VGPR、零spill、4KiB LDS。完整C32模块73a2dfdb…，两档三组200帧ABBA逐位：900 −0.29543ms、1080 −0.45633ms。

新增DynamicFrames，按fixture生成位移/增益/黑白输入、seed=123+17*f，首帧null history、后续前一帧输入作history。每帧先baseline后candidate，同步完成后比最终RGB；两档各16帧完整C32全逐位。它证明Network入口的数学/历史输入一致，不替代NativeGameFrame完整宿主生命周期。

wave-owned-combined生成host把C32和MH候选接到同一Network，mode0 prod8、1 MH36块、2 C3210块、3合用46块。MH模块cc8166b3…（C64/C128整块融合+C256 attention-only，非DirectFeature），C32模块73a2dfdb…。两档三组200帧ABBA：900配对−0.70055/−0.70633/−0.70033ms，均−0.702405ms，11.661035→10.958630ms，耗时−6.0235%；1080−1.10831/−1.10106/−1.09592ms，均−1.1017625ms，16.693508→15.591746ms，耗时−6.5999%。全部槽首尾逐位、46块/帧计数正确；组合也完成两档各16帧动态历史对照，全逐位。

所有source生成器、原始日志/CSV、module manifest与校验脚本归档。未部署、未宣称游戏FPS提高相同比例。下一步可选生产集成、gfx1200编译、NativeGameFrame完整回归，再测真实游戏；后续继续研究ViT/C512/布局。6.6%是阶段结果，尚未实现用户要求的质变，也未证明Daniel42%的精确贡献分配。
