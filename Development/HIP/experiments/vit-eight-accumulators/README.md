# ViT八累加片段：偏A重用还是偏B重用

基线56d11ef。16×128与32×64都计算2048个输出/完整wave，8个累加片段；K1024/N4096、K顺序/激活/舍入不变。前者每K16读A1/B8，后者A2/B4。M640时同为1280个wave，M400后者832个wave、前者800，尾块BM1避免额外矩阵运算。两种形状均交叉行布局和连续片段A。

真实block31，8组配对（原核对两种行布局、同布局两形状、两形状各自A布局对照、打包+矩阵对原路径）。每项两轮ABBA，约100ms预热/400ms计时，计时前反码填充+完整预检、后检；原网络首尾FP32校验。只读ADL，不改频率。双架构编译，仅gfx1201实跑。测ISA/寄存器/驻留上限后再解释；整网无收益不采用。

结果：208微槽及6400整网计时帧完成，均通过输出检查，整网未见足够稳定收益，不采用。prepare-u2.py在prepare.py后运行，生成保留u4并追加u2导出的模块；prepare-network.py同时测片段32×64/u4和u2。collect.ps1收全部数据，analyze.py验证208微槽/32网络槽。inspect-isa.py对汇编，extract-metadata.py读取实际HSACO metadata，occupancy-u2.cpp同时查询NUM_REGS与HIP驻留上限。报告见../../../results/vit-eight-accumulators-20260922/README.md。
