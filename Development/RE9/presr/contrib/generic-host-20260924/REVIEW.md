# 网友投稿：通用 OptiScaler 宿主（"统一 RE9 和普通版"），2026-09-24 审

原件 7 个文件（微信收到，BOM/CRLF 已去掉存这里；原 patch 文件带 BOM，git apply 直接拒）。目标：把 RE9 那条"命令列表切分"路线推广到所有 DLSS 游戏，扔掉 ReShade addon 路线。

## 逐条

| 文件 | 内容 | 判断 |
|---|---|---|
| QueryStateBook.h + patch-commandlistproxy | 记录未闭合的 GPU 查询区间；切点处没有开着的查询就允许切（原来一见 BeginQuery/EndQuery/Resolve 就拒切） | **对**。D3D12 只要求 Begin/End 同列表。补丁在干净上游也打不上，只是上下文行少了一句注释（`rawInterfaceEscaped` 那行的尾注），手工可合 |
| patch-submissionhooks + patch-d3d12hooks | `_ReturnAddress()` 在游戏 exe 模块内的 CreateCommandList 提前包成可切分代理（原来等交换链之后、且 ProxyWrap 开启才包） | **合理**，保守。代价：游戏所有直接列表走代理，开销没量 |
| patch-lmxxfbackend | 模块目录、pendingJob 守卫、Submitted 队列检查、retire 返回值、rebindish——**全是我们 prepare-host.py 已有的改动**；新增的只有"切分被拒原因写进状态栏/日志"。**缺我们的曝光 ABI v2 两行**（fi.exposure…），说明基于我们更早的快照 | 只取"原因日志"那一条 |
| prepare-host.py / build-runtime.sh | 克隆同一 pin（8f71f73）、打上面的补丁、用 mingw 编 runtime | **runtime 编错了**：不打我们的 LmxxfNrRuntime.cpp.patch（fit-large、尺寸校验、曝光），等于退回 0.26 时代的 runtime；宿主 dxgi.dll 的 MSVC 构建一字未提 |

## 结论

方向对（真统一了，卧龙的同列表绘制、2077 的别名资源都天然解决，不用 ASYNC 查表），两处宿主改动值得合进 `Development/RE9/presr/prepare-host.py`；但没有任何测试证据（哪个游戏、帧率、画面），runtime 部分不能用。合入前要：手工合 CommandListProxy 那一处；把早期包裹和查询记账加进我们的 prepare-host；用 build-host.ps1 编宿主；剑星实测帧率与 addon 路线对比（RE9 路线的同步切分对剑星 60 帧是不是有代价）。
