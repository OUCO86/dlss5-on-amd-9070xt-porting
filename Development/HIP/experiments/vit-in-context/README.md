# 真实网络前序下的pack+ViT展开段

使用上一轮32×64/片段A/u2候选；每帧8pack+8expand替换。只在block31的pack前与expand后放一对HIP事件，每计时帧单独事件对象，不做234核逐个计时。没有CPU回读/同步插在被测段内；原有每帧完成同步保留。

四组各两轮ABBA：plain_ab（原核/候选无事件）、marked_ab（原核/候选都标记block31）、marker_base（仅原核标记开关）、marker_candidate（仅候选标记开关）。每槽30预热+160计时；GPU事件读数在槽计时外获取，逐项正值/有限/完整标记校验，完整原始FP32校验，记录替换数与只读ADL。先1080后900。

该段时间含同一stream中两核之间的调度/供数间隔，不是纯矩阵指令时间。首先用marker控制量测量扰动；扰动明显时不能把标记时间当原始分项耗时。与此前热微段host wall口径不同，不直接把两者差值当缓存周期。

## 本轮结果

短段直接事件三次失败：结束事件同步、逐帧同时同步起止并立即读取也不能去掉非正时标，原样保存拒收证据。prepare-prefix.py/run-prefix.ps1改用两个长前缀的交错差分；长区间校验过，但小差值噪声大。prepare-region.py/run-region.ps1测首次pack→block38整个区域，并做marker开销控制。完整报告在../../../results/vit-in-context-20260922/README.md；本轮不修改生产。现有prepare.py生成的是最后的立即读取短段候选；旧两个exe哈希及失败数据留档。
