# ViT FFN 真实输入台阶

prepare.py 固定读取 8bca0f7 的 deep_fast.hip，生成 /tmp/vit-ffn-ladder/kernel.hip 和 pure.cpp。编译 host：x86_64-w64-mingw32-g++ -std=c++17 -O2 -static -D_WIN32_WINNT=0x0A00 /tmp/vit-ffn-ladder/pure.cpp -o /tmp/vit-ffn-ladder/pure.exe。

上传 host/source/build.ps1/run.ps1 至 amd9070 D:\DLSSNR-Lab\hip-backend\vit-ffn-ladder；build.ps1 双架构编译，run.ps1 游戏进程守卫后测900/1080的首个展开与收缩（block31）。基准模块来自 mh-empty-c256-modules，保持其他模块不变。collect.ps1 收集证据，analyze.py RESULTS_DIR ASM_FILE 生成报告。

保留原始导出；新增 raw/act 导出及独立 epilogue。每方案两轮 ABBA，与同模块原导出对照；raw/act 补尾部之后逐字节同原输出，split 整链直接比较。收缩保留残差初始化及四段累加顺序。中间 FP32 流量是实验的一部分，不能把拆分耗时当成消除融合后开销。运行无逐核事件，host wall + stream sync 批计时，完整网络首尾逐位检查。
