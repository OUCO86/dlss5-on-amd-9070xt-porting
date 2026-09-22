# 算力缺口：读取宽度、矩阵/供数重叠与工作规模

目的为解释完整权重的缺口，不是生产优化。双架构COMGR编译、gfx1201执行，全部在独立lab目录运行。

## 初始区分

把相邻两个K16片段排成每lane连续16字节。pair64与pair128使用相同新布局、相同矩阵顺序/数据/算量；前者源码8字节读取，后者16字节。先用model4原布局作布局校准。ISA实际将pair64的A合并为2条128位，B仍16条64位；pair128则A2+B8条128位。两者16WMMA/循环、75VGPR，故真正宽度干预在B。

pair128_adjacent在源码中改变独立累加器的遍历顺序，但编译器恢复成与pair128相同的汇编，不能当实际发射顺序干预；作为同代码控制保留。

numeric.cpp用非均匀FP8 -1/16、0、1/16验证原/新布局，K1024、三个wave，CPU整数点积/256给出精确参考；每个kernel检查96个lane的完整校验和。不是完整矩阵逐元素验证，也不覆盖任意浮点舍入场景。

## 去矩阵控制及其校准

load-only.inc保留10条128位读取，移除WMMA，用单条整数XOR链消费所有加载分量。load-multi.inc改为20条独立链，最后合并，排查校验依赖本身。这些核有额外整数运算、寄存器/调度变化，CSV的load_ceiling标签不代表纯缓存物理带宽上限；它们不报告矩阵TFLOPS。两个版本均以CPU非均匀校验和验证。

## 固定分配，再固定工作集

400与640下去矩阵核表现相反。prepare-grid.py保持同一进程、同一A640KiB/B4MiB分配及地址，只切换派发规模。prepare-rows.py再把输入row映射到固定256行，确保A/B访问集合不因400→640扩大；同时测试496/512/528。row折叠入口与原多链入口先校准。因合成数据均为1/16，地址折叠不改变预期校验和，不用于真实网络。

全部沿用计时外D2D调理、10个chunk约400ms的host wall/sync，两轮ABBA；按chunk关联ADL，不修改频率/功耗。RGP另作重复热核捕获，不拿其百分比拼独立计时。

## 文件对应

kernel.hip+bench.cpp/numeric.cpp为原宽度实验；prepare-extended.py生成extended模块/宿主；prepare-multi.py生成multi；prepare-grid.py生成固定分配宿主；prepare-rows.py生成rows模块/宿主。生成物在/tmp/wmma-width-gap。build.ps1和run.ps1支持-Extended/-Multi；run-grid.ps1、rows.ps1分别执行固定分配/固定工作集对照。宿主MinGW C++17/O2/static编译。capture.ps1/counter.cpp捕获pair64/pair128/去矩阵多链，collect.ps1归档。下一方向由结果决定，不预设加宽即可填满缺口。

本轮完成：[报告](../../../results/wmma-width-gap-20260922/README.md)。168槽2520590计时launch/336次全lane检查通过，14个非均匀kernel实例×96lane检查通过，三捕获9次/无捕获3次checksum通过。

宽B读取去掉约33% L0请求、但只少约9% L2请求；宽度本身没有填完缺口。同进程同地址、固定A256行/B4MiB后，496→512反而26.467→17.869μs，说明固定字节带宽解释不足。没有将去矩阵核称作纯带宽上限，也没有根据HIP驻留容量猜实际队列。下一轮固定实际wave数与工作集，只改变工作组组织及其逻辑wave映射，先用同代码/同输出控制校准；目标为区分服务时序与重用，不筛选生产优化。
