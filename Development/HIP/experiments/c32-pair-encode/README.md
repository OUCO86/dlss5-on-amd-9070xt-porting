# C32 收缩后成对编码

仅改收缩后16个结果的RTZ半精度转换及FP8量化组织。mode1将相邻两结果放进同一条pkrtz指令；mode2共享一次双值FP8转换；mode3同时采用。保留残差half存储的原有强制转换、FP8饱和、矩阵顺序、共享内存布局及barrier。原函数与候选同模块，隔离host按槽切换所有C32融合调用。

目标是直接比较等价融合核，不再用有4～9%扰动的编码重复探针估原生比例。先核验双架构生成ISA、单值/配对转换的边界结果，再做两档整网ABBA、逐槽完整FP32及替换数检查、只读ADL。旧输入配对和概率配对均无稳定收益；本轮针对尚未配对的收缩后RTZ+FP8链，不重做那两处。

prepare.py在/tmp生成源码与host，不改生产。build.ps1复用network-fixed-shapes/selected-modules，只替换实验目录的C32模块；gfx1200/gfx1201编译，运行gfx1201。primitive.cpp测试全部65536个half值及其相邻f32表示、100万伪随机f32位型，每项和逆序输入组成一对，比较舍入后两float、保存half、FP8两字节。

计划验收：生成指令确实减少且保留WMMA/LDS布局；真实融合核/整网收益稳定才考虑生产，不把静态指令数比例叫作周期占比。若减少指令但不提速，检查寄存器、拆字节、依赖与调度变化，记录负结果。

补充mode4：直接保留RTZ产生的half位元，省去残差保存时的再次f32→half；prepare-retain.py生成独立模块和host。mode3/4补做prefix、chain、post完整核热重复对照。

本轮已完成，四项均不采用；[结果报告](../../../results/c32-pair-encode-20260922/README.md)记录ISA、两档整网及完整核测量。
