# C32 输入和尾部探针

prepare.py 从固定 8bca0f7 生成诊断模块及纯 HIP 回放 host，输出 /tmp/c32-edge-cost；用 MinGW C++17 -O2 -static -D_WIN32_WINNT=0x0A00 编译 pure.cpp。上传 kernel.hip/pure.exe/build.ps1/run.ps1 至 amd9070 的 D:\DLSSNR-Lab\hip-backend\c32-edge-cost，先 build.ps1 双架构编译，再 run.ps1。collect.ps1 收集 CSV、日志和工件 hash；analyze.py RESULTS_DIR ASM_FILE 生成阶段报告/资源表。

保留所有原导出，诊断导出用 windows 高四位编码重复次数。输入轮末统一同步，prefix 投影每轮重置累加器；尾部重复相同写出。所有产出缓冲逐槽比较，网络首尾检查。输入/尾部不是彼此可相加的原生耗时分解，不用于发版。
