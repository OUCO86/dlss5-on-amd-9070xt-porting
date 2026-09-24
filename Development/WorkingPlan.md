# 当前工作计划（覆盖式，不续写；最后更新 2026-09-25 01:30，Hikari）

> 这个文件只记"现在打算做什么、等什么"，每次直接覆盖。已完成的事进 DevHistory.md，不在这里重复。开 session 先读这页再动手。
> 节奏：过日子式，没有 deadline。有兴致就挑一把逐位的小刀试，没兴致就写文章、回 issue。

## 状态

- **prod7 已装剑星**（09-24 07:13）：prod6 + mh_fast 全行写，逐位，回归通过；备份 backups\20260924-071340（`install.ps1 -RestoreBackup`）。用户实玩：900P 中画质拉伸 2K 常测场景稳定 60 帧。**进 0.30**（三包 + README 更新记录，复制 package-029.ps1 改版本号和 hash；等用户说打包）。
- **0.29 已发布**（09-23，三包，链接在 README 更新记录）：内核 = prod6（栅栏 + 折叠 FFN + 字节链 + 注意力寄存器化 + in16 别名 + 尾段转置，全逐位，相对 0.28 约 −7%）+ `DLSS5_FIT_LARGE`（超 1080p 输入）。剑星装的就是这套；实玩 900P 简单场景约 60 帧，网友最低画质 73 帧。
- **6b（非逐位，仅研究，未装）**：`HIP_FFN_WAVE_NORM` 再 −1.1%，12 帧 RGB 差 PSNR 58 dB、1.4% 像素 >1/255、max 0.17。源里默认 0。要不要装进游戏看闪不闪，用户随时可拍板，不催。
- **318 初稿已写**（wechat/318.md，八章），等用户过稿并补 313/324/325 的公众号链接。
- 研究结论：必要损失七八成（算法非矩阵工作、8×8 窗口形状税、L2 之下的供数税、launch 尾巴）；已回收 7%；放弃逐位最多再 1% 左右。三条规则——读写成本 ≈ 指令数 + 触及行数；驻留只在它是瓶颈时值钱；同一改法赚不赚看该核当下被什么卡住（阶段账要在当前驻留下重打）。

## 机上现状（09-24 21:00）——三处待收尾

- **prod8 候选待装**（`deployments/stellar-prod8-20260925/install.ps1`，含 flags 写入与回滚；回归过，比 prod7 约 −1.2% @900）。进 0.30：模块 prod8 两架构 + 插件 5be18ac3… + 模板 `DLSS5_HIP_PDL=1`。
- **剑星 + 赛博朋克都装了 0.30 候选 addon a569ed6f…**（21:50；`deployments/addon030-strength-20260924`，`install.ps1 -Restore` 可退）：双钩子（shim + provider dispatch，线程局部深度防重入）+ `ASYNC=auto` 查表 + **`DLSS5_STRENGTH=auto` 查表（Cyberpunk2077.exe → 1,0 只转亮度，其他 1,1）**。两处 flags 的显式 STRENGTH 行已删，由表决定；剑星显式 ASYNC=1、赛博显式 ASYNC=0 + OptiScaler.ini `EnableFfxInputs=false`，和模板 auto 行为相同。**等用户玩 2077 确认 1,0 动态场景没问题、剑星无变化。**
- **2077 红偏已定位**（DevHistory 21:10 条）：前置线性域取神经色相再过游戏 LUT 会转色相；只转亮度细节增益不丢。Magpie 后置 1080p 细节多一截但 30 帧对 51 帧，结构代价不是 bug。
- **生化 9 已装 prod7 内核**（`deployments/re9-prod7-20260924`，`install.ps1 -Restore` 可退），抓帧验过神经路径确实在改细节（不是只变亮度）。
- **"只有光影变化"的担心已量化**：高通对数亮度 RMS 比 / 相关 / 梯度幅值比——纯调色是 corr≈0.9997、比 1.0；剑星 1.11/0.887/+13%，赛博 1.00/0.973/+13%，生化 1.03～1.13/0.98/+19%，都不是纯调色。图在各 deployments 的 detail-crop-*.png。
- **网友"统一 RE9 与常规包"补丁审完**（`Development/RE9/presr/contrib/generic-host-20260924/REVIEW.md`）：查询记账 + 提前包裹两处可用，backend 补丁是我们 prepare-host 的旧翻版，runtime 脚本没打我们的补丁不可用，无测试证据。**等用户问到他在哪个游戏跑通、帧率多少再定**要不要合进 prepare-host.py 用 MSVC 编宿主到剑星实测。

## 0.30 打包（等用户说打包）

复制 package-029.ps1 → package-030（版本号、hash）；内核 prod7；addon a569ed6f…（strength-auto）；常规包 OptiScaler.ini 叠加 `scripts/optiscaler-regular.ini`（`[Inputs] EnableFfxInputs=false`，对剑星空操作）；flags 模板 `ASYNC=auto`（Cyberpunk2077.exe 查表→同步）；README 更新记录一行，夸克 + Google Drive 两链接；帧率：剑星 900P→2K 中画质 60～61，赛博 低画质 900P→2K 50～51。README 已有"分游戏说明"段和 0.29 的 Google Drive 链接。

## 卧龙 2（Alpha Demo 被 Steam 卸载，机上残留已清）

等它装回来：常规包 + EnableFfxInputs=false + ASYNC=0（或把 WoLong2.exe 加进查表）+ 0.30 addon 重试；"同列表后有 draw"那条是真障碍，别名那半可能同赛博朋克。若网友的切分宿主真跑通，卧龙这类天然解决。

## 下一批探索（09-24 00:50 从 318 三张账本里挑出来的，按值不值得排；先做 1 和 3）

1. ~~直达共享内存的读取~~（09-24 01:00 验过：gfx1201 没有 `vmem-to-lds-load-insts` 特性，comgr 拒绝 builtin，汇编器也不认 `global_load_lds_b128`——RDNA4 根本没有这条指令，是硬件没铺路，不是我们不会写。关。）原文：RDNA4 `global_load_lds`，数据从显存直接落 LDS，不经寄存器、不占向量发射。先验两件事：comgr 上 builtin 在不在（`__builtin_amdgcn_global_load_lds`）、gfx1201 支持到多宽（传闻 gfx12 有 b128）。落点按 lane 线性排，packed 行距 36 字节不线性，要改行距或改读法。逐位天然成立。唯一没碰过的"搬运方式"级改法。
2. **L0 黑箱再量一层**（第三章"L2 命中 99.95% 但停顿 68%"）：受控小程序量 L0 每 CU 每周期送多少字节、地址低位到 bank 的映射（bit10 敏感已摸到一角）、请求合并规则。不直接提速，决定第一格"必要损失"是真必要还是地址排布撞了它。
3. ~~频率当第四张账本~~（09-24 01:05 做完，`results/clock-ledger-20260924`）：是功耗墙，板功耗钉 325～328 W，时钟随核族变——FFN(C64～C256) 最费电（占满时 −8～9%），ViT 最省电（+1～2%），整网 2.75 是加权。后续两件：(a) 318 第一章"ViT 单测 2.5 GHz"改口；(b) 已追到：FFN 的电烧在全局窄写（norm +4%、norm+out +7% 时钟），ALU/LDS/barrier 不耗电，并宽指令不省电（触及行数没变）。**全行写做完（01:30）**：逐位，−0.6/−0.7%，FFN 占满时钟 +1.2%（没到 +7%：字节没少，只省了部分写）。prod7 候选回归通过（`deployments/stellar-prod7-20260924`），**等用户关游戏装机**。用户侧：Adrenalin 功耗上限 +10% 值得剑星实测。
4. ~~launch 尾巴用两条流盖住~~（09-25 01:30 做完，改道：双流在这驱动上不并发、事件一对 110 μs；同流 `hipExtAnyOrderLaunch` + tile 旗子（土法 PDL）逐位，**900 −1.6%、1080 −0.6%**，`results/pdl-chain-20260925`。**prod8 候选**（两模块两架构 + 插件 + `DLSS5_HIP_PDL=1`）regression-prod8 过（逐位；对 prod2 900 −6.3%/1080 −5.7%，比 prod7 约 −1.2%/−0.5%），**等用户关剑星装机**。还能挤：等旗子那次 L2 往返没法和核开头重叠；C512 链 13×7 个小 launch 和 ViT 同一套机制可搬，核各不相同要分别接；Down/Up/pool 接旗子链头也能任意序。）
5. **mapped/post 输入按 tile 顺序写**：chain 类已是 tile 顺序 + 128 位读；mapped/post 读行主序 f32 十六行散读。让 HLSL 编码 / 合并层按 tile 顺序写，这两核读等待砍一半，估整网 1% 上下。"生产者按消费者布局写"的最后一处。
6. **旧 null 重测前先解谜**：wave 局部栅栏（LOCAL_FFN/ATTN_SYNC）09-16 null 是旧驻留下的，现在 barrier 等待 8.7%；但后来记录它和 lane staging 组合后哈希变了，先搞清为什么不逐位。

## 可以慢慢做的（无序，看心情）

- 逐位小刀：host 侧宽权重片段（−0.03ms）和小 launch 合并，等哪次因别的事重编 addon 时顺带。（C32 产出端并宽 09-24 试过：逐位同但慢 0.03ms，已关。）
- 非逐位第二处（只在用户认可 6b 画质之后）：C32 QKV 归一化同型改法（先消融定上界）；ViT/C512 K 分块累加顺序。
- 网友反馈跟进：超宽屏 fit-large 实机、9060 系列、RE9 帧生成/HDR。issue 来了照旧：能修就修，修完进下个包。
- 6b 若要装：编 gfx1200 的 6b mh_fast、做只换 mh_fast 两架构的 payload、装机由用户看画质。

## 不做 / 已关

CU 模式逐核、C32 转置尾部并宽、C32/C512/ViT 注意力寄存器化、split_projection 转置尾声、BatchNorm 合并 barrier、ffn_fused VGPR 封 96、注意力残差读提前、注意力投影输出转置、注意力行和改 VALU、c256 注意力尾巴（结构税）。

## 机器与流程

**git（09-24 用户定）：只 commit/push 本仓（297），不再往外层 ai-theorys-study 提指针提交。**

9070 机器 `amd9070`，工作根 `D:\DLSSNR-Lab\hip-backend\`；编译 `dual-arch-src\rtc_compile.exe <out> <src> comgr gfx1201`（输出旁自带 .hsaco.s）；跑前 `check-idle.ps1`；长 ssh 用后台任务。实验模板：kernel 后缀 ABBA（c32-lds-alias）、模块集 ABBA（mhfast-vgpr-cap；容忍 bitdiff 的 host 在 mhfast-tail-ablate）、核内打点（launch-occupancy）。候选流程 deployments/stellar-prod6-20260923（build → regression → payload → install）；发包 Development/tools/package-029.ps1（下次复制改版本号和 hash）；**发布 = 夸克 + Google Drive 双上传**（09-24 起，Google 给没有中国手机号的用户），README 两处链接都要写。生产配方：c32 = ISA_HALF+PREPACKED+C32_DIAG，mh_fused = ISA_HALF+MH_RTZ_ISA，mh_fast = ISA_HALF+PREPACKED+FFN_HOIST_RES 2，deep_fast = ISA_HALF+PREPACKED+BRANCHLESS_F。
