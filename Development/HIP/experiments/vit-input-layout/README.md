# ViT输入布局对照

prepare.py固定b1be848，输出/tmp/vit-input-layout/kernel.hip和pure.cpp；MinGW C++17 -O2 -static -D_WIN32_WINNT=0x0A00编译pure.exe。build.ps1双架构；run.ps1按1080→900测matrix/pack/pair/dynamic_control，来自真实block31。CPU置换检查tiled输入所有字节，GPU产出反码填充+计时前后检查。

prepare-network.py生成network/network.cpp，同样编译为network.exe；run-network.ps1每帧只替换八次打包和八次展开，完整网络ABBA并核对FP32。现有正常模块来自network-fixed-shapes/selected-modules，实验只替换deep_fast-packed，未改生产源码/配置。

collect.ps1收集CSV/遥测/hash；analyze.py RESULTS_DIR验证80计时槽并生成summary.json。实际生成汇编保留于Windows模块旁，isa.json记录资源。参考结果和编码输入沿用network-timeline；Graph/自适应/历史关，post_shift=3。

这次布局试验无整网收益，不采用。下一轮计算密度探针继续沿算力缺口研究，不能将当前负结果写成排除所有输入访存问题。
