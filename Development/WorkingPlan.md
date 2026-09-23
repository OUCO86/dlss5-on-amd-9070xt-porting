# 当前工作计划（覆盖式，不续写；最后更新 2026-09-23 16:00，Hikari）

> 这个文件只记"现在打算做什么、等什么"，每次直接覆盖。已完成的事进 DevHistory.md，不在这里重复。开 session 先读这页再动手。
> 节奏：过日子式，没有 deadline。有兴致就挑一把逐位的小刀试，没兴致就写文章、回 issue。

## 状态

- **0.29 已发布**（09-23，三包，链接在 README 更新记录）：内核 = prod6（栅栏 + 折叠 FFN + 字节链 + 注意力寄存器化 + in16 别名 + 尾段转置，全逐位，相对 0.28 约 −7%）+ `DLSS5_FIT_LARGE`（超 1080p 输入）。剑星装的就是这套；实玩 900P 简单场景约 60 帧，网友最低画质 73 帧。
- **6b（非逐位，仅研究，未装）**：`HIP_FFN_WAVE_NORM` 再 −1.1%，12 帧 RGB 差 PSNR 58 dB、1.4% 像素 >1/255、max 0.17。源里默认 0。要不要装进游戏看闪不闪，用户随时可拍板，不催。
- **318 初稿已写**（wechat/318.md，八章），等用户过稿并补 313/324/325 的公众号链接。
- 研究结论：必要损失七八成（算法非矩阵工作、8×8 窗口形状税、L2 之下的供数税、launch 尾巴）；已回收 7%；放弃逐位最多再 1% 左右。三条规则——读写成本 ≈ 指令数 + 触及行数；驻留只在它是瓶颈时值钱；同一改法赚不赚看该核当下被什么卡住（阶段账要在当前驻留下重打）。

## 可以慢慢做的（无序，看心情）

- 逐位小刀：C32 产出端 `out` 16 条字节写并宽（要连 FFN 收缩、saved_ffn、ffn8 一起转置，改动大，估 ≤0.5%）；host 侧宽权重片段（−0.03ms）和小 launch 合并，等哪次因别的事重编 addon 时顺带。
- 非逐位第二处（只在用户认可 6b 画质之后）：C32 QKV 归一化同型改法（先消融定上界）；ViT/C512 K 分块累加顺序。
- 网友反馈跟进：超宽屏 fit-large 实机、9060 系列、RE9 帧生成/HDR。issue 来了照旧：能修就修，修完进下个包。
- 6b 若要装：编 gfx1200 的 6b mh_fast、做只换 mh_fast 两架构的 payload、装机由用户看画质。

## 不做 / 已关

CU 模式逐核、C32/C512/ViT 注意力寄存器化、split_projection 转置尾声、BatchNorm 合并 barrier、ffn_fused VGPR 封 96、注意力残差读提前、注意力投影输出转置、注意力行和改 VALU、c256 注意力尾巴（结构税）。

## 机器与流程

9070 机器 `amd9070`，工作根 `D:\DLSSNR-Lab\hip-backend\`；编译 `dual-arch-src\rtc_compile.exe <out> <src> comgr gfx1201`（输出旁自带 .hsaco.s）；跑前 `check-idle.ps1`；长 ssh 用后台任务。实验模板：kernel 后缀 ABBA（c32-lds-alias）、模块集 ABBA（mhfast-vgpr-cap；容忍 bitdiff 的 host 在 mhfast-tail-ablate）、核内打点（launch-occupancy）。候选流程 deployments/stellar-prod6-20260923（build → regression → payload → install）；发包 Development/tools/package-029.ps1（下次复制改版本号和 hash）。生产配方：c32 = ISA_HALF+PREPACKED+C32_DIAG，mh_fused = ISA_HALF+MH_RTZ_ISA，mh_fast = ISA_HALF+PREPACKED+FFN_HOIST_RES 2，deep_fast = ISA_HALF+PREPACKED+BRANCHLESS_F。
