# 同launch多份独立工作

prepare.py从11bc0ad生成/tmp/vit-work-scale/kernel.hip、pure.cpp；MinGW C++17 -O2 -static -D_WIN32_WINNT=0x0A00编译pure.exe。build.ps1双架构编译，其他模块来自network-fixed-shapes/selected-modules；run.ps1按1080→900运行。默认2种行tile×2种排列×4种份数，每配置两轮ABBA，副本输出不别名。SCALE_FILTER可限定major或interleave。

prepare-streams.py在上述生成目录追加独立输入跨度探针，输出streams.hip、streams/streams.cpp，编为streams.exe；build-streams.ps1双架构，run-streams.ps1补1080八份共享/分离输入地址。同一kernel用stride=0或T×1024切换，其余参数和分配相同。streams.csv的shared_input列表示对照方向，不是原生产核。

两种host计时前与计时后都验证全部输出；原核比较也写相同scratch首区域，结束恢复网络原输出。每个副本共享相同真实权重，分离输入对照数值相同但地址不同。拓展工作集/改变索引也可能影响时钟和缓存，不能把批量吞吐等同单帧提速。

collect.ps1收CSV/遥测/hash，analyze.py RESULTS_DIR校验288槽和6次原始输出，并计算每份时间及配对时钟参考。首次漏Frag模板的失败数据单独归档拒收；正式计时不含该错误。
