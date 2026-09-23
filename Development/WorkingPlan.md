# 当前工作计划（覆盖式，不续写；最后更新 2026-09-23 16:05，Hikari）

> 这个文件只记"现在打算做什么、等什么"，每次直接覆盖。已完成的事进 DevHistory.md，不在这里重复。开 session 先读这页再动手。

## 状态

- **已装剑星：prod6**（11:28）= prod2 + prod5（字节链 + mh 注意力寄存器化）+ C32 in16 别名 + ffn_fused 尾段转置，全逐位；相对 prod2 −4.3%（900）/ −4.5%（1080），相对最初约 −7%。备份 `stellar-prod6-20260923\backups\20260923-112851`，回退 `install.ps1 -RestoreBackup`。实玩反馈（13:41）：900P 简单场景最快接近 60 帧，无异常。
- **6b（非逐位，仅研究，未装）**：prod6 + `HIP_FFN_WAVE_NORM`（wave 内 QKV 归一化），再 −1.1%（合计 −5.4/−5.6%）。12 帧 RGB 差：mean 4.3e-4、PSNR 58 dB、1.4% 像素 >1/255、max 0.17（个别边缘像素）。源里默认 0，只有 gfx1201 模块。**当前唯一待拍板的事：要不要装到游戏里看闪不闪。**
- issue #6（超 1080p 输入 `DLSS5_FIT_LARGE`）已完成并实测（剑星、RE9），代码在 main（addon c1bc7374…、RE9 runtime 6e9974d7…），发包时自然带上。
- 研究结论（进 318）：必要损失约 25～30%；可回收的已回收约 7%；三条规则——读写成本 ≈ 指令数 + 触及行数（转置并宽只对"展开的多条窄写"有效，原版是滚动循环别动）；驻留只在它是瓶颈时值钱；同一改法赚不赚看该核当前的瓶颈（阶段账要在当前驻留下重打）。

## 待办（按顺序）

1. 6b 画质：用户想看的话，编 gfx1200 的 6b mh_fast、做 6b payload（只换 mh_fast 两架构）、装机由用户在游戏里判断。不想看就关闭这条。
2. **318 成稿**：初稿已写（wechat/318.md，八章 + 收尾，约 2.5 万字），等用户过稿；313/324/325 的公众号链接由用户补进正文。旧素材版在 git 历史里。
3. 还可以试的逐位小刀（各估 ≤0.5%）：C32 产出端 `out` 16 条字节写（要连 FFN 收缩、saved_ffn、ffn8 一起转置，改动大，先看 C32 输出段的静态写是不是"展开的多条窄写"——是）；host 侧宽权重片段 / 小 launch 合并等 addon 重编顺带。
4. 非逐位第二处（只在用户认可 6b 画质之后）：C32 QKV 归一化同型改法（C32 用的是 ones-WMMA 平方和，先消融定上界）；ViT/C512 K 分块累加顺序。

## 不做 / 已关

CU 模式逐核、C32/C512/ViT 注意力寄存器化、split_projection 转置尾声、BatchNorm 合并 barrier、ffn_fused VGPR 封 96、注意力残差读提前、注意力投影输出转置、注意力行和改 VALU、c256 注意力尾巴（结构税）。

## 机器与流程

9070 机器 `amd9070`，工作根 `D:\DLSSNR-Lab\hip-backend\`；编译 `dual-arch-src\rtc_compile.exe <out> <src> comgr gfx1201`（输出旁自带 .hsaco.s）；跑前 `check-idle.ps1`；长 ssh 用后台任务。实验模板：kernel 后缀 ABBA（c32-lds-alias）、模块集 ABBA（mhfast-vgpr-cap；容忍 bitdiff 的 host 在 mhfast-tail-ablate）、核内打点（launch-occupancy）；候选流程 deployments/stellar-prod6-20260923（build → regression → payload → install）。生产配方：c32 = ISA_HALF+PREPACKED+C32_DIAG，mh_fused = ISA_HALF+MH_RTZ_ISA，mh_fast = ISA_HALF+PREPACKED+FFN_HOIST_RES 2，deep_fast = ISA_HALF+PREPACKED+BRANCHLESS_F。
