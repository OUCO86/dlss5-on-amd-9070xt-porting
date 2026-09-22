# 算力缺口：固定wave总数，改变工作组组织

问题：上一轮固定地址/工作集后，读取核仍有非单调规模曲线。本轮固定M640/N4096/K1024、2560wave、数学工作和访问元素集合，只改变每组wave数及逻辑wave映射，不筛生产候选。

- i映射：logical_wave=group*W+local_wave，组内相邻列块共享A、读取不同B列块。
- m映射：logical_wave=(group/64*W+local_wave)*64+group%64，组内相邻行块共享B、读取不同A行块。
- W=1/2/4/8分别为32/64/128/256线程；总wave数不变，工作组数为2560/W。输出按logical_wave存放，不因派发映射改变。
- 每wave的循环仍10条128位读取；矩阵版16条WMMA/循环，读取版无WMMA、用20条独立XOR链。循环16次。跨映射前缀地址计算不同，不能声称完整ISA逐字相同；记录编译器资源和HIP容量查询。

先用W1对旧pair128/读取多链作校准，再比较i1→i2/4/8，及同W的i→m。计算/字节总量不变，实际重用时序与并发、请求局部分布会变；正结果不能单独命名为调度器或某级cache机制。

数值验证使用非均匀FP8三值，CPU整数点积/256或XOR参考。每入口发一个工作组，按映射核对所有活动lane，同时检查其余81920输出word仍是canary，防止漏写/越界。数学模式的每个输出仍为32个累加分量的校验和，不是矩阵逐元素比较。CPU另校验全网格映射是2560wave的双射。

沿用同进程固定A640KiB/B4MiB、计时外D2D、两轮ABBA、10chunk约400ms以及只读ADL，不改频率设置。采样百分比/静态驻留上限不等于动态队列。双架构COMGR，gfx1201运行。

prepare.py生成/tmp/wmma-groups-gap/kernel.hip和bench.cpp（复用上轮生成器及头文件）；MinGW C++17/O2/static编译宿主。build.ps1/run.ps1只操作相应独立lab目录。

## 校准与拆分

prepare-uniform.py为逻辑wave编号增加readfirstlane，显式告知编译器wave内相同；同组2wave矩阵版实际VGPR从76回到75，仍约42.9μs，未解除慢点。不能仅用额外逐线程地址计算解释分组效果。

prepare-order.py保持每组1wave、2560组，只用logical_wave=(group*stride)%2560置换编号，stride1/17/63/129均为全网格双射。每个逻辑任务仍访问原地址、输出原位置；改变的是派发编号与任务的映射，不保证硬件按编号顺序执行。先校准旧i1与stride1，再同机码比较不同stride。非均匀CPU参考/全输出canary检查用三个工作组，覆盖被置换的输出位置。

capture.ps1及capture-order.ps1另作64dispatch热重复RGP计数，不混入D2D调理wall。main研究仍未有全网百分比分账：历史整个ViT约占12～14%，当前样本只是其中部分，C32约35%尚未闭合机制。

本轮完成：[结果与解释覆盖评估](../../../results/wmma-groups-gap-20260922/README.md)。224槽2253820计时launch/448次全lane校验和通过；36个非均匀CPU参考/canary案例通过。五份纯HIP捕获各64dispatch/三次checksum通过，无捕获两组各三次通过。原始trace保留远端及/tmp，解析计数器/hash入库。

下一优先级回到历史约35%耗时的C32：复用请求账本思路，区分真实路径的矩阵工作、格式转换/LDS交换与同步/服务。先回读已完成的phase/edge/ISA报告，避免重做探针；不将ViT的供数结论直接套到整网。ViT的动态时序和精确周期份额仍未闭合，先留明确未解项。
