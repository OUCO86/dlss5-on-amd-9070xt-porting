# 单wave窗口候选组合

prepare.py生成MH已验证host，再加入C32派发；复用生产模块和两个独立原型module。mode0 prod8；mode1 C64/C128融合+C256 attention-only（36块）；mode2完整C32（10块）；mode3合用（46块）。MH片段权重固定W2_FRAG=1，C32采用RollHidden+RollWindow，CU mode。

prepare-modules.ps1复制模块并记录全部hash；不修改游戏。两档固定输入ABBA与RGB槽首尾逐位，DynamicFrames额外从同一原fixture生成位移/增益/黑白帧，每帧非零种子，第一帧无历史、后续传前一帧输入作为历史；同一Network同步切baseline/candidate，逐帧与当场算出的baseline RGB比较。此项验证网络的历史输入数学与调用计数，不替代NativeGameFrame完整runtime资源生命周期回归或真实游戏FPS。

本目录不复制kernel实现，依赖c64-wave2/c32-wave1；模块快照由results下modules-manifest.json精确标识。prepare.py的host摘要另存manifest.json。
