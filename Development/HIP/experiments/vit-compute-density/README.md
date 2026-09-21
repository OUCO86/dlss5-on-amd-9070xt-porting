# 保持读取、增加诊断矩阵工作

prepare.py固定b2df1a5，输出/tmp/vit-compute-density/kernel.hip、pure.cpp。MinGW C++17 -O2 -static -D_WIN32_WINNT=0x0A00编译pure.exe；build.ps1双架构；run.ps1真实block31，1/2/4/8倍WMMA与2/4/8空控制，各两轮ABBA。每槽输出反码填充后完整校验，首尾原始网络校验。

首版使用B空读写约束，控制组扰动大。prepare-seeded.py生成seeded.hip，额外WMMA的C初值不同以防CSE；prepare-uniform.py将每个C向量各分量统一、组间不同，降低常量寄存器开销。对应build/run-seeded、build/run-uniform各自独立目录，使用同一个host。最终主论据为uniform-1080，900运行状态不稳，只归档。

模块都保留原始导出、只增加probe导出；额外WMMA结果通过只读asm观察而不写网络输出。必须从生成ISA确认16/32/64/128 WMMA、20 global_load_b64、K64循环16次且无spill；仅数源代码不算验证。高倍率的TF包含冗余工作，不是推理加速。

collect.ps1收全部三批，analyze.py RESULTS_DIR核对336槽/12次原始输出并计算配对时钟参考。解释及下一步平衡tile计划见results/vit-compute-density-20260922/README.md。
