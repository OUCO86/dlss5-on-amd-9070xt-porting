# 当前工作计划（覆盖式，不续写；最后更新 2026-09-24 18:30，Hikari）

> 这个文件只记"现在打算做什么、等什么"，每次直接覆盖。已完成的事进 DevHistory.md，不在这里重复。开 session 先读这页再动手。
> 节奏：过日子式，没有 deadline。有兴致就挑一把逐位的小刀试，没兴致就写文章、回 issue。

## 状态

- **prod7 已装剑星**（09-24 07:13）：prod6 + mh_fast 全行写，逐位，回归通过；备份 backups\20260924-071340（`install.ps1 -RestoreBackup`）。用户实玩：900P 中画质拉伸 2K 常测场景稳定 60 帧。**进 0.30**（三包 + README 更新记录，复制 package-029.ps1 改版本号和 hash；等用户说打包）。
- **0.29 已发布**（09-23，三包，链接在 README 更新记录）：内核 = prod6（栅栏 + 折叠 FFN + 字节链 + 注意力寄存器化 + in16 别名 + 尾段转置，全逐位，相对 0.28 约 −7%）+ `DLSS5_FIT_LARGE`（超 1080p 输入）。剑星装的就是这套；实玩 900P 简单场景约 60 帧，网友最低画质 73 帧。
- **6b（非逐位，仅研究，未装）**：`HIP_FFN_WAVE_NORM` 再 −1.1%，12 帧 RGB 差 PSNR 58 dB、1.4% 像素 >1/255、max 0.17。源里默认 0。要不要装进游戏看闪不闪，用户随时可拍板，不催。
- **318 初稿已写**（wechat/318.md，八章），等用户过稿并补 313/324/325 的公众号链接。
- 研究结论：必要损失七八成（算法非矩阵工作、8×8 窗口形状税、L2 之下的供数税、launch 尾巴）；已回收 7%；放弃逐位最多再 1% 左右。三条规则——读写成本 ≈ 指令数 + 触及行数；驻留只在它是瓶颈时值钱；同一改法赚不赚看该核当下被什么卡住（阶段账要在当前驻留下重打）。

## 游戏适配进行中：《赛博朋克 2077》（09-24，详见 DevHistory 末条）

机上：常规包 + 探针 addon（钩 upscaler dll、状态表补齐、DLSS5_PAPER_WHITE/DLSS5_DUMP_FRAME），flags：EnableFfxInputs=false（OptiScaler.ini）、**DLSS5_PRE_UPSCALE_ASYNC=0**（关键：别名瞬态资源）、PAPER_WHITE=1、DEBUG_DUMPS=1/DUMP_FRAME=3000（验完删）。等用户实机看 ASYNC=0 + 纸白 1。通过后：README 加"REDengine/Katana 类游戏：EnableFfxInputs=false + ASYNC=0"，剑星回归（addon 改了钩子顺序/状态表），进 0.30 的 addon。**卧龙 2 也回头试 ASYNC=0**——它那条"同列表后有 draw"是真的，但灰画面那半也可能是同一别名问题。

## 搁置的岔路：《卧龙 2》Alpha Demo（09-23 夜，详见 DevHistory 末条；09-24 00:20 用户定：先放一边，回主线优化）

机上现状：装的是 RE9 宿主变体（无 REFramework），`EnableFfxInputs=false`、`LmxxfDiagnostic=off`，游戏内动态分辨率已关。神经路径已生效但画面灰、多数帧绕过。要做两处 Katana 化：
1. 曝光发现：RE9 的曝光扫描过滤在卧龙上撞出 >64 个候选，先用 `capture-colour.request` 抓一帧看 FP16 输入范围和真实曝光值，再决定是收紧过滤还是走固定曝光/无曝光归一化。
2. 提交观察：`prior job not yet submitted` 反复——`LmxxfBackend::Submitted` 只认同一队列且不在逻辑 Execute 内，卧龙的提交队列/时机不同，要放宽或改观察点。
做完后：剑星回归（`src/native_submission_order_probe.cpp` 的钩子顺序改了），常规包 README 记"Katana 引擎游戏需 EnableFfxInputs=false + 关动态分辨率"。不急，网友那边先回"正在适配"。

## 下一批探索（09-24 00:50 从 318 三张账本里挑出来的，按值不值得排；先做 1 和 3）

1. ~~直达共享内存的读取~~（09-24 01:00 验过：gfx1201 没有 `vmem-to-lds-load-insts` 特性，comgr 拒绝 builtin，汇编器也不认 `global_load_lds_b128`——RDNA4 根本没有这条指令，是硬件没铺路，不是我们不会写。关。）原文：RDNA4 `global_load_lds`，数据从显存直接落 LDS，不经寄存器、不占向量发射。先验两件事：comgr 上 builtin 在不在（`__builtin_amdgcn_global_load_lds`）、gfx1201 支持到多宽（传闻 gfx12 有 b128）。落点按 lane 线性排，packed 行距 36 字节不线性，要改行距或改读法。逐位天然成立。唯一没碰过的"搬运方式"级改法。
2. **L0 黑箱再量一层**（第三章"L2 命中 99.95% 但停顿 68%"）：受控小程序量 L0 每 CU 每周期送多少字节、地址低位到 bank 的映射（bit10 敏感已摸到一角）、请求合并规则。不直接提速，决定第一格"必要损失"是真必要还是地址排布撞了它。
3. ~~频率当第四张账本~~（09-24 01:05 做完，`results/clock-ledger-20260924`）：是功耗墙，板功耗钉 325～328 W，时钟随核族变——FFN(C64～C256) 最费电（占满时 −8～9%），ViT 最省电（+1～2%），整网 2.75 是加权。后续两件：(a) 318 第一章"ViT 单测 2.5 GHz"改口；(b) 已追到：FFN 的电烧在全局窄写（norm +4%、norm+out +7% 时钟），ALU/LDS/barrier 不耗电，并宽指令不省电（触及行数没变）。**全行写做完（01:30）**：逐位，−0.6/−0.7%，FFN 占满时钟 +1.2%（没到 +7%：字节没少，只省了部分写）。prod7 候选回归通过（`deployments/stellar-prod7-20260924`），**等用户关游戏装机**。用户侧：Adrenalin 功耗上限 +10% 值得剑星实测。
4. **launch 尾巴用两条流盖住**（C256 注意力尾巴 25～37%，一帧 0.15ms）：窗口注意力只看自己窗口、错位只跨相邻窗口，按图像上下两半拆两条流串事件，N+1 上半盖 N 下半的尾巴。核不动逐位不变，改提交结构。先把各核尾巴都量一遍定上限。
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

9070 机器 `amd9070`，工作根 `D:\DLSSNR-Lab\hip-backend\`；编译 `dual-arch-src\rtc_compile.exe <out> <src> comgr gfx1201`（输出旁自带 .hsaco.s）；跑前 `check-idle.ps1`；长 ssh 用后台任务。实验模板：kernel 后缀 ABBA（c32-lds-alias）、模块集 ABBA（mhfast-vgpr-cap；容忍 bitdiff 的 host 在 mhfast-tail-ablate）、核内打点（launch-occupancy）。候选流程 deployments/stellar-prod6-20260923（build → regression → payload → install）；发包 Development/tools/package-029.ps1（下次复制改版本号和 hash）。生产配方：c32 = ISA_HALF+PREPACKED+C32_DIAG，mh_fused = ISA_HALF+MH_RTZ_ISA，mh_fast = ISA_HALF+PREPACKED+FFN_HOIST_RES 2，deep_fast = ISA_HALF+PREPACKED+BRANCHLESS_F。
