# C32完整窗口一wave原型

独立实现，额外模块可替换四个非finish chain块（block2/3/67/68）、两个mapped首块（block1/66）和两个finish块（block4/69）；其他模块仍为prod8。原始输入/输出沿用窗口顺序FP8，保留shift/crop边界和补零。prefix和post尚未替换。

- 32线程负责64token；输入每lane读原生A片段，FFN展开转置输出直接送收缩。
- 三段对角残差、K16累加次序、Hrtz、FP8转化均保留。
- Q/K转置计算，归一化仍是原C32的两次FP16 WMMA平方和；V直接生成B片段。
- Q/K/V留寄存器；softmax保留C32顺序四个K16归约与norm_inverse双步修正，不用多头核的交错归约。
- AV直接送projection。FFN原始半精度残差存4KiB LDS，按当前query读回；单wave内读写，不用组barrier。
- host只改目标kernel派发，候选mode 1/2/3/4分别替换chain/mapped/finish/全部，目标计数每帧8次，替换4/2/2/8次；RGB首尾逐位对照现有fixture，ABBA整网计时。固定输入筛选不等于多帧历史回归。

prepare.py生成/tmp/c32-wave1，MinGW编译network.cpp；build.ps1编译gfx1201，run.ps1测900/1080。Launder可选让每个tile的lane坐标成为独立编译器值，限制跨tile片段缓存；不是数值近似。RollHidden可选保留隐藏片段循环，QkvFence隔离QKV子段坐标/排程；Wgp关闭原生产CU mode；RollWindow保留窗口tile外层循环，用可统一索引的向量保存Q/K/V，避免动态C++数组溢出。开关都默认关。结果归档Development/results/c32-wave1-20260926。

首块mode0残差沿用输入先转半精度再乘scale，矩阵输入仍按原float转FP8；不能复用已量化字节来算残差。finish复用FFN残差的4KiB平面写入最终half结果，按原顺序执行裁切/F转化/2×2下采样，无新增全局临时张量。
