# ViT剩余算力缺口对照

prepare.py固定70656f8，生成/tmp/vit-gap-controls/kernel.hip和pure.cpp。MinGW C++17 -O2 -static -D_WIN32_WINNT=0x0A00编译host，build.ps1编译两个架构，仅替换当前network-fixed-shapes/selected-modules的deep_fast-packed。run.ps1测10种展开/合组/工作顺序/行重用变体，计时前输出逐字节反码填充，验证完整写出和整网原始输出。

timing.inc支持GAP_FILTER；初扫pure.exe为未加过滤的host，过滤版编成pure-filter.exe，run-repeat.ps1只测u4并按1080→900排序。prepare-prime.py在/tmp副本生成prime/prime.cpp，编成prime.exe；run-prime.ps1用同一个原核，改变计时前负载（原核忙200ms或128MiB缓冲D2D忙200ms），都再预热50ms，测200ms。没有改硬件设置；这是运行状态诊断，复制成本不算收益。

occupancy.cpp编成occupancy.exe，collect.ps1读取运行时驻留上限并收集三批数据；analyze.py RESULTS_DIR验证192槽、12次原始输出并配对只读ADL时钟。汇编kernel.s另保存在Windows模块旁，isa.json记录静态资源；静态WMMA数量可能含fallback/多token分支，不能直接当每次执行数。

报告在results/vit-gap-controls-20260921。900热核时钟/基线不稳，初扫不排名；1080稳定数据用于调度比较。M2旧动态尺寸下已有历史实验，本轮是在固定尺寸的新基线上复测，不能沿用旧“排除权重重读”的强结论。
