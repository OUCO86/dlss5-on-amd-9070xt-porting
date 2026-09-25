# C32完整窗口一wave原型

独立实现，额外模块替换四个非finish chain块（block2/3/67/68）；其他模块仍为prod8。原始输入/输出沿用窗口顺序FP8，保留shift/crop边界和补零。不改prefix、mapped首块、finish或post。

- 32线程负责64token；输入每lane读原生A片段，FFN展开转置输出直接送收缩。
- 三段对角残差、K16累加次序、Hrtz、FP8转化均保留。
- Q/K转置计算，归一化仍是原C32的两次FP16 WMMA平方和；V直接生成B片段。
- Q/K/V留寄存器；softmax保留C32顺序四个K16归约与norm_inverse双步修正，不用多头核的交错归约。
- AV直接送projection。FFN原始半精度残差存4KiB LDS，按当前query读回；单wave内读写，不用组barrier。
- host只改目标kernel派发，计数每帧4次；RGB首尾逐位对照现有fixture，ABBA整网计时。固定输入筛选不等于多帧历史回归。

prepare.py生成/tmp/c32-wave1，MinGW编译network.cpp；build.ps1编译gfx1201，run.ps1测900/1080。Launder可选让每个tile的lane坐标成为独立编译器值，限制跨tile片段缓存；不是数值近似。RollHidden可选保留隐藏片段循环，两个开关都默认关。结果归档Development/results/c32-wave1-20260926。
