# ViT循环调度因果对照

prepare.py从固定8bca0f7生成/tmp/vit-schedule-cause/kernel.hip、pure.cpp；MinGW C++17 -O2 -static -D_WIN32_WINNT=0x0A00编译为pure.exe。上传到amd9070 D:\DLSSNR-Lab\hip-backend\vit-schedule-cause，build.ps1双架构构建，run.ps1游戏进程守卫后用真实block31输入测五种变体；ADL只读遥测按Windows uptime配对。

prepare-network.py生成/tmp/vit-schedule-cause/network/network.cpp，以相同编译选项编成network.exe。上传后run-network.ps1只替换整网8次ViT展开或收缩，做正反向ABBA。collect.ps1收全部证据；analyze.py RESULTS_DIR ASM_FILE验证CSV并汇总单核/整网及配对时钟。

变体保持原算术和数据流：固定尺寸自动展开、固定尺寸禁展开、动态尺寸提示unroll4、固定尺寸显式unroll4、收缩禁展开。检查汇编确认实际生成行为，不把pragma当作执行证据。所有原导出保留；两种host都核对完整输出。正常推理头文件仅在/tmp副本加实验hook，生产源未改。
