# 算力缺口：固定工作集，只改B tile物理间距

承接wmma-feed-gap的非单调B span曲线，目的为区分原因，不是生产优化。

**假说**：慢点主要依赖地址映射/请求分布/缓存或地址转换的冲突；改变tile物理间距后，即使逻辑访问元素数与计算不变，也可能显著移动慢点。

**竞争解释**：主要是矩阵依赖链或总传输量；相同计算、相同加载条数、相同不同元素数，仅加未读取的padding，不应产生大的变化。

span64/128/1024分别对应256KiB/512KiB/4MiB逻辑B访问集合。原N16 tile之间相距16384字节；加64/128/256/512/1024字节。所有条件共用同一4.25MiB B分配，内容全为FP8 1/16；不改变分配容量。A保持完整，M640/N4096/K1024，共5.36870912GFLOP，WMMA与加载数量恒定。

每种span先比较旧masked4与新pitched4的16384间距，校准加入运行时pitch的编译/资源扰动。真正padding比较只在同一pitched4机器码内改一个参数。不能把跨入口差直接当地址效果。

沿用计时外D2D调理和chunk测量，2505MHz显存须通过遥测确认。每槽pilot与计时后全lane checksum，所有累加分量参与；不是网络输出检验。每项两轮ABBA，预热约100ms，10个chunk合计约400ms。无短段HIP事件。

地址间距同时可能影响cache映射、TLB/页足迹、请求分布，正结果不能直接指认某一级cache；还须计数器或更细对照。负结果同样保留，不改生产tile。

双架构COMGR编译，gfx1201运行。bench.cpp用MinGW C++17/O2/static编译；build.ps1/run.ps1只操作D:\DLSSNR-Lab\hip-backend\wmma-pitch-gap。

## 已完成与后续验证

144槽、1801510次计时launch、288次全lane checksum检查通过。span64的慢点随padding显著移动，span1024改善很小。四次纯HIP RGP捕获各64dispatch、各三次校验和同，无profile控制三次同；原始trace只保留远端及/tmp，解析JSON/hash入库。

prepare-real.py生成当前正式网络的隔离host，只将首次ViT展开重复10000次。先无捕获两帧验证，再用capture-real.ps1捕获第3000附近64dispatch并完成1000帧；两进程首尾四次整网原始FP32同。真实原核L0 hit57.826%、L2 hit99.947%、memory unit stalled68.404%，支持实际供数背压，但不是自然整帧时间分账。源码生成器、实际宿主/模块/输入hash、捕获日志与解析数据归档。

[结果报告](../../../results/wmma-pitch-gap-20260922/README.md)。下一步优先围绕真实完整权重集合区分缓存服务吞吐、请求分布和在途请求/依赖限制；如果继续细分特殊span64地址效应，可在原tile首4KiB内做不同偏移，保持高位地址不变以减少页足迹混杂。仍只为归因，不当生产优化候选。
