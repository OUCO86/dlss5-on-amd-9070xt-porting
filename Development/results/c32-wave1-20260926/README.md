
## 2026-09-26：C32完整窗口单wave链式原型逐位跑通

独立额外模块c32-wave1替换block2/3/67/68四个非finish chain。保留输入输出窗口FP8、shift/crop补零、三段残差对角、C32专用FP16平方和与四个K16顺序softmax归约。Q/K/V寄存器驻留，FFN展开转置直接收缩，AV直送projection；4KiB LDS只存FFN半精度残差，单wave无需组barrier。

首版两档各三组200帧ABBA、每槽首尾RGB逐位同，每帧4次替换计数正确：900 −0.05340ms、1080 −0.08415ms。VGPR240、零spill，module380a5da9…；收益仅约0.5%，不当成目标完成。跨tile地址隔离版本239VGPR、零spill，1080 −0.06430ms（同样三组逐位）；没有实测改善。FFN隐藏片段滚动循环对照也完成1080三组逐位：−0.10293ms，VGPR仍240，module efc870c3…；与首版差仅约0.019ms且跨批，不据此断言额外提升。后续优先扩大到mapped/finish，再查prefix/post布局。未改生产/部署，多头组合与完整历史回归尚待。
