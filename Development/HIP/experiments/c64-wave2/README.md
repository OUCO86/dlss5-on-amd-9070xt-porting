# 一头一wave的独立Swin原型

首个C64版本：64线程/两wave，一个wave负责一个head的64个token。保留生产算术与行主序外部激活接口，独立实现，未使用Daniel二进制代码。

- 两个4096B LDS平面，均按WMMA原生A片段排列。input→contract→feature→AV按存活期复用，仅跨head混合时同步；共4次组barrier。
- 分组FFN展开→收缩直接在寄存器间传片段，通过操作数交换得到所需转置；128项分组收缩与原K顺序相同。
- Q/K按A片段、V直接按B片段计算并驻留寄存器，V不经过转置缓冲。一个head的四个query tile在同一wave内执行。
- Q/K归一化保留32项f32顺序，用4次wave内部分和传递跨越每8项边界；未采用半精度树归约。softmax保留既有两组FP16 WMMA求和次序。
- 融合FFN/QKV/attention/projection，移除这几段之间的global特征/归一化流。外部输入/输出仍走原格式，不把布局转换成本藏到别处。

实验host从当前生产源生成副本，仅指定通道走新模块。其他生产模块来自prod8，基线PDL=1；新核普通同流提交，正确处理PDL前序结束。每帧目标调用计数、RGB逐位与ABBA检查。

首版只有固定输入两档筛选通过，尚未经过完整多帧历史回归，也未装机。性能与后续扩展见 `Development/results/c64-wave2-20260926`；目标仍是找到并实现足够大的整网收益，首个约1%的结果不是目标完成。

扩展版本模板覆盖C64/128/256，mode 1/2/3分别替换，4全部，5仅C64+C128。build/run参数Layout、Launder、Schedule、RollQuery、HiddenTiles成对设置；当前最佳混合筛选为frag+Launder+Schedule+RollQuery+HiddenTiles 2、Candidates 5。Schedule只约束编译器排程，不添加GPU组同步。analyze.py复核ABBA与替换计数。完整回归待做。

C256拆分实验mode 6：保留生产FFN/QKV，仅替换attention/projection。输入仍是[pixel][Q,K,V][channel] FP8，feature单独FP8；先在AV平面暂存V并转B片段，所有head加载后复用为AV。生成器复用完整核的attention/projection段，保持归约顺序。新核256线程、8wave，PDL输出累计目标从16调整为8；前段FFN的计数不变，同一slot跨模式累计不同增量。保留现有PDL可见性/复用协议，不能据逐位测试宣布其待审问题已解决。gfx1201编译float/byte输出分别151/142VGPR，零spill。

mode 7组合C64/C128整块融合与C256仅attention替换，共36块；mode 6/7不支持DeferQ，因Q已由生产者归一化。运行组合实验与单族实验分别统计，不直接相加各自收益。
