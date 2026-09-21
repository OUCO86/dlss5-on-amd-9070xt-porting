# 固定尺寸的全网筛选

prepare.py 固定基线2f4c8fa，保留全部正常导出，四个模块增加诊断入口；输出 /tmp/network-fixed-shapes。八位mask逐项选择：1 ViT展开、2 ViT投影、4解码投影、8池化投影、16 C512注意力、32 C512位移/池化、64 ViT注意力token、128 ViT QKV token。audit.md覆盖当前默认路径234调用。

MinGW C++17 -O2 -static -D_WIN32_WINNT=0x0A00编译network.cpp；初扫host为network.exe，后续参数化host为network-repeat.exe。build.ps1编译四模块双架构；run.ps1跑默认八组900/1080 ABBA。环境NFS_VARIANT/NFS_BASELINE/NFS_FRAMES控制单组重测；run-decoder-repeat.ps1比较mask3/7、400帧。每槽检查原始FP32和每帧实际替换数，ADL只读遥测。

prepare-selected.py --decoder生成三个选中改动的正常ABI源码及packed/unpacked编译输入（不带--decoder仅前两项）。build-selected.ps1双架构编译两模块，其余模块复制当前mh-empty-c256基线。regression.ps1沿用逐帧RGB与千帧ABBA，run-regression.ps1顺序执行正常/运动与额外720/history/float控制。collect.ps1保存初扫；collect-final.ps1保存叠加、回归CSV/逐帧hash/最终模块hash。二进制保留在Windows实验目录。

初扫只做单因素筛选，不把不同槽基线直接相减，不把全部细微正值自动采用。正式源码与验证后的selected-source.hip对齐，无新画质开关或ABI更改。
