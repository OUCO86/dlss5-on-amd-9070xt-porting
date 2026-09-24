# DLSS5（DLSSNR）→ AMD RX 9070 XT 移植：开发史

> 本文件是本项目开发、部署、运维与后续工作的**唯一记录入口**。
> **2026-09-23 压缩**：原文 593KB（约 30 万 token）已整本移到 `Development/history/DevHistory-full-20260923.md`（git `a300c20` 之前的完整版）。本文只留结论、关键数字、现行约定和"别再做"的清单；要查某一刀的细节、SHA、日志路径，去原文 grep 日期或关键词，别整本读。
> 更早的逐刀原始记录在 `Development/history/` 其余文件（见文末索引）；每轮实验的数据在 `Development/results/<名字>-<日期>/`、`Development/HIP/experiments/<名字>/`。

**续写规则**：
- 新事件**直接追加在文件最末尾**（§12 流水，时间正序，`## 日期 时间：标题` + 正文），不要往 §4 的表里塞，也不要插到中间。
- 「§3 当前状态」「§11 待办」原地改；新的"不要重做"补进 §7，新教训补进 §8。
- §12 长到读不动时：每天压成 §4 的一行，结论并入 §5～§8，原文照样挪进 history/。

---

## 1. 目标与硬约束

把 NVIDIA 泄露样本 `nvngx_dlssnr.dll`（DLSS 5 神经渲染，内部名 DLSSNR）里的 71 块网络恢复出来，在 RX 9070 XT 上按原版数值执行，并在真实游戏里以可玩帧率替换 FSR 输出。

- 验收三级：离线复现 → AMD 跑通 → 游戏可用。后来 Zero 收紧为"9070 XT 走完 71 块出最终 RGB"，再到 1080p ≥10fps，再到 30fps。
- **exact 链**（tag 0.01，186ms）逐值等于原版，冻结当裁判；**fast / HIP 链**：结构改动必须逐位不变，算术改动看 PSNR，画面由 Zero 在游戏里按 F6 拍板。
- 帧率只信游戏内读数或同批 ABBA；绝对帧时跨批次留 ±0.3ms。

| 机器 | 用途 |
|---|---|
| `desktop-2026`（`ssh amd9070`），Win11 Insider 26H2，RX 9070 XT（RDNA4，gfx1201，16GB，128 SIMD / 32 WGP） | 靶机 |
| `NucBox_EVO-T1`（`ssh rtx5090`），RTX 5090 OCuLink | 标准答案机（原版 DLSSNR） |
| DGX Spark `spark-3a10`（GB10，sm_121） | 能直接加载 sm_120 CUBIN 当 oracle |

驱动：DX12 路线需要**预览驱动 32.0.31007.2048**（SM 6.10 / LinAlg，私有 Agility 721、开发人员模式）。HIP 路线（0.20 起）只需驱动自带 `amdhip64_7.dll`，不要预览接口；正式驱动有用户反馈可用。

---

## 2. 逆向结论（硬事实，不会再变）

**样本**：`nvngx_dlssnr.dll` 310.8.0.0，SHA-256 `e16bcf15…1fc8e`。资源 `WEIGHTS_HT` 147,695,410 字节，153 条记录（`name_length→name→body_span→body`），live 层对象 152 个（block70 的 blend_scale 与 layer 同属一个 Layer）。矩阵主体是 packed E4M3，偏置/skip/scale 是 FP16/f32；运行时 arena 按 512 字节对齐，共 147,719,680 字节，运行时不改写权重。DLL 内含 15 个 sm_120 CUBIN。

**网络**（构图函数 `0x180039780`，config `hnet-vigilant-squid` / variant `crazy-cuckoo`）：
```
0        PreBlock 1H / C32          1–3 Swin C32   4 ds 32→64
5–7      Swin 2H / C64              8 ds 64→128
9–13     Swin 4H / C128             14 ds 128→256
15–21    Swin 8H / C256             22 ds 256→512
23–30    split-Swin 16H / C512（30 带 ProjPool + FinalHead 512→1024）
31–38    ViT 1D / C1024（Expand→Contract→QKV→Attention→Projection）
39       DecInputUpsample 1024→512  40–47 split-Swin C512
48/56/62/66 upsample + Swin（C256/C128/C64/C32），49–55 / 57–61 / 63–65 / 67–69 同族
70       PostBlock C32 + RGB 头（blend_scale=0.73974609375）
```
跳接：`39←38+30`、`48←47+22`、`56←55+14`、`62←61+8`、`66←65+4`、`70←69+0`。

**1080p 几何**：处理区 1920×1152（底部 72 行镜像，`2*extent-coord-2`），ViT 20×32 = 640 token（有效 18×30）；post shift 3。decoder 移位 40–55 = 0/3/1/2 循环，56–61 = 1/2/0/3…，62–69 = 0/3/1/2（`native_runtime_shifts.h` 唯一）。900 档是我们自定的几何：1600×900 有效、**1600×960 处理**（09-17 定，原 1024 行版保留为 `900w`），ViT 25×16，第 16 行是零 token。

**NGX 输入**：Color / Output（1080p RGBA16F）/ Depth / MVec；history（slot8）= 上一帧网络输出，motion 在 slot10；`input_scale=1/32`，`rgb_mode=1`。

**算术**：
- FFN 激活 `x=clamp(x,-4,4); y=x*(0.89453125+x*(0.447265625-0.055908203125*|x|))`（half 多项式，不是 GELU）。
- 残差 skip-first：`H(input*skip)` 作为初始累加器，之后每 K32 做一次 half 舍入；FP8 是 E4M3 SATFINITE、RNE，次正规尾数允许进位到 8。
- 注意力：每 head 32 维，Q/K 归一化用半精度平方和，归约顺序固定；softmax 的 exp 是 half 仿射加移位的位映射（C32、ViT 系数不同）；分母求和树是固定的 key 顺序，不是平衡树。
- C64 三矩阵 FFN：64→256（分组扩展）→64（分组收缩，**每 32 输出通道只连 128 hidden，其余全零**）→64（混合）；C512 split FFN 是 512 混合→8 组 64→256→64。
- 输入混合按 WMMA 规则：两操作数指数和的最大值对齐，按 `2^(E-27)` 朝零截断后精确求和。随机场是 Box–Muller，用 MUFU 近似。
- 时序采样：UV 定点 21 位，五点十字核，MUFU.RCP 归一化。
- post70：输出合同是 `Color + 神经残差`；RGB 头两个 K16 的 27 位对齐整数规则。
- 原版 FP16 输出 surface 是**朝零截断**；AMD 预览驱动的 `f32tof16` 也是朝零截断。

---

## 3. 当前状态（2026-09-23 16:00）

**《剑星》装机版 = prod6**（HIP，OptiScaler 前置链，900P auto）：Zero 实测 900P 简单场景接近 60fps，无异常。备份 `D:\DLSSNR-Lab\stellar-prod6-20260923\backups\20260923-112851`（回退 `install.ps1 -RestoreBackup <该目录>`）。addon 后来换成 FIT_LARGE 版 `c1bc7374…`。用户个人 flags 里 `ADAPTIVE=1`（ViT 复用开）。

**发布**：0.29 三包已在 `D:\給網友打包`（Magpie `fb005c3e…`、OptiScaler `55142927…`、OptiScaler-REFramework `668133f9…`），清单 `Development/releases/0.29/packages.json`；**网盘链接待 Zero 上传后补进 README**。0.28 三包及 RE9 0.28.1 链接已在 README。

**黄金 hash**（HIP 900 档正确性回归）：900w 三道 `FEEA9EF3…`（40 帧）/ `22C171FC…`（每 8 帧 reset）/ `75B62D2F…`（seed123 history）；960 三道（900 漏派发修复后）`047c36e1…` / `b4f66e9d…` / `0e4afd83…`。HLSL 参考 `C7C2F49D…`。脚本 `validate-modules.ps1`、`validate-modules-960.ps1`。

**性能**：离线 900 档约 12.1ms、1080 档约 17.3ms（prod6，完整 NativeGameFrame 回放）；HLSL 900 约 16.8ms。网友 900P 最低画质 73fps。

**未装的研究候选**：6b（ffn_fused wave 内 QKV 归一化，非逐位，−5.4/−5.6%，PSNR 58dB）等 Zero 看画质；ffn_fused_c256 宽权重片段（约 −0.03ms，host 打包器改动，等下次 addon 重编时顺带）。

---

## 4. 时间线（里程碑）

| 日期 | 事件 | 关键数字 |
|---|---|---|
| 08-31 | 权重解析、71 块构图恢复、5090 跑通原版、AMD 上传 arena | 153 条记录 |
| 09-01 | block0 出图、SASS 解出算术；row-major 假设被反证（矩阵按 tensor-core tile 排列） | |
| 09-02～03 | 在 5090 游戏 backend 里抓 live 中间层，用"下一层当裁判"逐段前移 | block70 RGB corr 0.945 |
| 09-04 | 动态游戏链 484s→10.6s；DirectML；1080p 单 DLL 进游戏 | 11.98fps |
| 09-05 | 像素审计翻案（此前根本没提交），8×8 网格 → 停追 FPS，改做 native 正确性 | |
| 09-06 | 原生逐值链 RGB512→0–70→RGB 全 exact；实机几何 640 token | 786,432 值 diff 0 |
| 09-07 | valid1080 整网 exact、时序 exact、进游戏出正确画面；闇夜战 4.0s→1.47s | 2fps |
| 09-08 | 闇→0.47s；光→0.186s（**tag 0.01 exact 终点**）；fast 链到 62.7ms（0.03） | 5→15fps |
| 09-09 | 33ms，GPU 饱和；显存之争（6.8→3.75GB）；闪烁靠输出平滑；0.04～0.06 | 29fps |
| 09-10 | fast38 34.0ms；0.07 包；浪人崛起 XeSS 出图；发现机器降频态（重启后 24.4ms） | 35fps |
| 09-11 | Magpie 路线打通；黑块根因 = 硬件 E4M3 Cast 不饱和 → NaN；全仓 43 处加饱和（0.10）；接管时间 22s→3.4s（0.11） | |
| 09-12 | 屏幕提示层（0.12）、FPS 显示 + XeSS FG（0.13）、0.14；C512 FFWD 换 FP8 无收益，"项目收尾" | Magpie 28→55 显示帧 |
| 09-13 | 小窗口 FIT_INPUT（0.15）；720 / 900 分支 | |
| 09-14 | **HIP 分支**：comgr 无 SDK 编译、D3D12↔HIP 桥接、512/900 逐位对上 oracle | |
| 09-15 | HIP 生产快路径 51→25ms；异步重绑竞态修复；读回节奏污染 HLSL 基准被识别 | 游戏 17→30fps |
| 09-16 | MH 分组收缩零结构、各家族 attention+投影融合、ViT 融合；"dup / 跳块"帧内成本法；权重预打包四连 | HIP 18.07 |
| 09-17 凌晨 | 读 `.s` 当 profiler：F() 去分支 + 16 load 连发（−0.68）、prefix 内联翻盘等 → **HIP 反超 HLSL** | 16.9→15.5ms，游戏 47→52fps |
| 09-17 | **0.20**（HIP，免预览驱动）；生产内核搬进 `hip/`；auto 选档（0.21）；900→960 行（0.22） | 900P 52～54 / 1080P 37～38 |
| 09-18 | 多 GPU 主机修复（0.23）；黑神话的钩子三道坎（未验通，已复原） | |
| 09-19 | OptiScaler 前置链（0.24）；主城掉帧修复；C32 寄存器复用 / 有界倒数；**900 解码尾部漏派发修复**；gfx1200 + gfx1201 双构建（0.25）；C256 frag；LOP 黑屏 = 打包漏 R11 shader（0.26） | |
| 09-20 | RE9 后置专用版（0.26.1）；从 AttExp 选入精确流式 attention / R3 自适应复用（默认关）；0.27 | 900P 56～57 |
| 09-21 | **算力缺口研究立项**（主线，见 §6）；C128/C256 零填充快路径、固定尺寸 ViT/decoder（−1.2/−1.7%） | |
| 09-22 | TheAutomatic PR5 设计独立实现分阶段桥接 → RE9 真正超分前接入 + 曝光修复（0.28、0.28.1）；合并 PR #7/#8；栅栏 local 化 + C32 CU 模式 | 58～59fps |
| 09-22 夜～09-23 | prod3～prod6：折叠 FFN、字节链、向量化 staging、mh 寄存器化、in16 别名、尾段转置 | 相对 prod2 −4.3/−4.5% |
| 09-23 | prod6 装机；DLSS5_FIT_LARGE（issue #6，>1080 输入降到 1080 层）剑星 + RE9 验通；**0.29 三包** | ~60fps；网友最低画质 73 |

---

## 5. 性能演进要点

### DX12 fast 链（09-08～09-12，186→约 24ms）
收益全部来自数据搬运：寄存器分块复用、FP8 格点上的中间量改用 f16 存、权重常驻 DEFAULT 堆、删 LDS 转存和 barrier、合批。**这台卡的核成本几乎全在逐元素标量尾巴**（软件 H/F、散写），不在带宽也不在矩阵乘。逐刀表见原文 §3「fast 链每刀收益表」。

### HIP 链（09-14～09-23，离线 900 档 51→12.1ms，全部逐位一致）
有效的几类刀，按类别记：
- **核融合**：各家族 FFN+QKV、attention+投影（C64/C128/C256）、prefix 进 block0、post RGB 头 / finish / 下采样进 C32 尾部。
- **权重预打包**：half / E4M3 / fragment 布局，一次 memcpy 取 B 片段；C512 QKV、ViT QKV / proj / contract、pool、decoder。
- **ISA 病灶**：F()/q8 的分支饱和改 fmin/fmax + cndmask；串行 load→wait 改连发；scale 读从循环里提出来。
- **结构零**：MH 收缩只遍历本组 128 K；C128/C256 全零 padding tile 直接写零。
- **固定尺寸**：编译期常量解锁展开与读取调度（ViT expand 一处 −26～36%）。
- **同步 / 驻留**：栅栏限定 LDS 地址空间（去掉 `global_inv`）、C32 用 CU 模式、in16 别名到 Scratch。
- **WMMA 操作数对调**（A/B 寄存器格式相同，对调得到 D^T）：折叠 FFN 让 hidden 不进 LDS、mh 的 ex/prob 留寄存器、ffn_fused 尾段转置。
- **请求合并**：C32 staging 把 16 条行读并成 b128（字节链 + 向量化）。

---

## 6. 算力缺口研究（318 期主线，09-21 起）

**问题**：9070 XT 独立程序实测 FP8 405T / FP16 204T / FP32 49.9T（与标称一致，时钟约 3.1GHz）；网络主矩阵有效吞吐只有约 55T。**判据是解释缺口，不是零碎提速**；负结果能排除原因也算数。总汇总 `results/network-cost-summary-20260921/README.md`，公众号稿 318.md。

已建立的认识：
1. **整网份额**（900/1080，稀疏事件 + 区段 ABBA）：C32 约 35%，C64 / C128 / C256 / C512 / ViT 各约 11～13%。局部机制证据**不能相加成整网解释百分比**。
2. **ViT 同 FLOPs 不同耗时**：expand/contract 的差异主要来自编译调度组织（固定尺寸解锁展开）；禁止 contract 展开慢 175%。
3. **计算密度探针**：保持读取量不变、只加寄存器内 WMMA，吞吐 150→299T，说明 150T 不是硬件上限，是供数和指令组织在限制。
4. **供数**：B 的工作集吞吐不单调；B tile 间距 +256B 后 span64 48→22μs；页内翻 bit10 同样有效 → 对地址低位敏感。真实 ViT 核在 RGP 里 memory stalled 68%（只代表那个热核状态）。
5. **规则**：读写成本 ≈ 指令数 + 触及的缓存行数，两项都算；lane 间仍连续时并宽才有效。排队按请求数算，不按字节数。
6. **分组 / 编号映射**：wave 总数固定时，组大小 1→2 或重排 logical_wave 编号都会慢 45%；HIP 驻留上限相同，原因未定。
7. **C32 周期账**（核内时间戳）：staging 31%、FFN 26%、QKV 11%、注意力 12%、投影 8%、尾部 9%、barrier 9%；矩阵只占 post 核约 15%。驻留贴着 LDS 上限。
8. **驻留**只在它是瓶颈时才值钱：VGPR 封到 96 反而慢；c256_attention 每个 launch 的尾巴 25～37% 是结构税。

仍未解：ViT 剩余约 50% 参考算力的具体限制因素；C32 余下部分的归因。

---

## 7. 已否定 / 不要重做（除非瓶颈变了，按"旧 null 要重测"原则说明理由再测）

- **占用率捷径**：C32 no-unroll（+0.64→+1.0 更慢）、waves_per_eu 提示（编译器不理）、LDS_SLIM、ffn_fused VGPR 封 96。
- **LDS 凑片**：C32 LDS_VECTOR（测了四次都是 null）、C32 / MH 的 V 转置、概率 DWORD 布局、AV 共读。
- **字节 / half 流**：MH 完整字节流当时慢（09-19 修漏派发后重测才通过，已进 0.25）；ViT byte/half stream、N2/N4 / M2 / M4、ViT FFN 融合（并行度不够）。
- **小通道 FFN 换布局**：C64/C128 tiled 或 frag（+0.3～0.4 更慢）。
- **C512**：mix 并进 FFN、FP8 展开（有逐位反例，只能收缩用 FP8）、attention+投影融合。
- **各种 hipGraph**：当前 GPU 时间把 CPU 提交全盖住了，收益为零。
- **C32 转置尾部并宽**（09-24：逐位同，慢 0.03ms；C32 卡读队列，写并宽不是瓶颈，转置反而让残差/缩放读变差）。
- **其他**：DX12 overlap（与游戏并发是双输）；VMM 稀疏映射（驱动只认"保留区 == 一个完整物理块"，封死）；buffer_load 32 位地址（正确，常量必须是 `0x31004000`，但无收益）；噪声缓存；多遍 NR（5090 上也不值）；C32 注意力寄存器化（压力抵消收益）；注意力投影输出转置（滚动循环别转置）。

---

## 8. 工程教训（合并版）

**测量**
- 只信同批交错 ABBA，别跨批比较绝对值；GPU 会卡在降频态好几天，量之前先跑基线。
- 逐核 HIP event 在这套驱动上不可靠，会出现负值，全插反而把帧时拉长 80%；短段事件也不能当依据。要么用 wall 加重复放大，要么用 dup / 跳块法（注意 HLSL 跳块带拷贝，会压低 HLSL 那边的家族成本）。
- 读回节奏会改变 GPU 频率：HLSL 全读回 26ms，只读首尾 16.7ms。性能测试一律只读首尾，正确性另做全帧检查。
- 单核隔离会把工作集留在缓存里，不能直接相加当整帧。
- `DLSS5_GAME_PROBE` 每帧 Flush，会破坏异步提交时序（地面变透明），不要和 ASYNC_SUBMIT 同开。
- 测帧率别开 Splashtop；先确认游戏有没有锁帧（剑星曾锁 30）。
- 派生测试脚本后先 grep runner 名；对照组没变化先怀疑脚本（09-16 两个假 null 就是这么来的）。
- RGP 捕获会改时钟和输出；RGP 里的 HLSL ELF 按占位哈希缓存，要先用 `dxilhash.py` 签名。

**数值**
- HLSL `round()` 是 RNE；`f32tof16` / D3D 驱动输出 surface 是朝零截断。
- FMA 收缩和上下文相关，凡要逐位的尾链两边都显式 `precise`。
- 单点候选能修一个反例，全幅上反而可能更差，别拿单点匹配去推广舍入规则。
- 单层高相关不等于多层稳定，必须做完整累计门。
- 硬件 E4M3 Cast 不饱和，所有无界值转换前都要 clamp ±448。

**GPU / D3D12 / HIP**
- 2 的幂行步长会让内存通道撞车；单 command list 塞整网会 DEVICE_HUNG，必须分块提交加 fence。
- D3D12 单轴 group 上限 65535；视图格式变量别复用（会建出 UNKNOWN 视图，device removed）；宿主贴图只能拷贝，不能建 UAV。
- ReShade immediate list 在 `_has_commands=false` 时直接 return，原生录的命令可能根本没提交。
- 派发网格按 token 和通道分别分块（900 档漏掉 4 个通道 tile 就是没这么做）。
- COMGR 确定性：同一文本两次编译字节一致，源码一变只改 `__hip_cuid_*`。校验标准 = 三道 hash + 去掉 cuid 后的 `.s` 对比。

**方法**
- 核内延迟问题先读 `.s`（数分支、数 load→wait、看重复 load），别凭结构直觉盲改。
- 跟 HLSL 并排逐段对"做同一件事但做法不同"的段。
- 旧 null 要重测：一刀的收益取决于当时的瓶颈。
- 静态指令数少不等于快；少 barrier 不等于快；少字节不等于快。

**运维**
- 游戏或 Magpie 开着时绝不换 DLL / HSACO，也不跑测试台。
- Windows Update 和 AMD Install Manager 会偷换驱动（已设 `ExcludeWUDriversInQualityUpdate=1`，计划任务已禁用）。
- 打包不能继承旧资产目录，要从仓库模板和当前源同步；配置唯一来源是 `scripts/*flags*.txt`（见 `scripts/CONFIGURATION.md`）。
- 远端 PowerShell 一律用 `-File`，别在 `-Command` 里 type 自己的输出文件（曾涨到 4.8GB）。
- commit 不加 Co-Authored-By；每做完一刀给 Zero 一句进度；时间只信 hook 时间戳。

---

## 9. 运维 / 构建 / 部署入口

- **目录**：生产宿主 `src/`、生产内核 `hip/`（`build-modules.ps1` 24 行配方，默认双架构，`SHA256SUMS`）、DX12 shader `shaders/`、打包与配置 `scripts/`；实验在 `Development/HIP/experiments/`，结果在 `Development/results/`，RE9 前置宿主在 `Development/RE9/presr/`（只入库版本锁定 + 补丁 + 脚本）。
- **AMD 机**：实验根 `D:\DLSSNR-Lab`（`hip-backend\` 放模块目录和 benchmark）；《剑星》在 `C:\Program Files (x86)\Steam\steamapps\common\StellarBlade\SB\Binaries\Win64`；成品在 `D:\給網友打包`。5090 的《剑星》在 `D:\SteamLibrary\…\Win64`。
- **构建**：`scripts/build-addon.sh --hip`（DX12 用 `--tiled`）；`hip/build-modules.ps1`。
- **部署**：每轮一个 `Development/deployments/<名字>/` 或 `D:\DLSSNR-Lab\stellar-<名字>\install.ps1`，流程是源 hash 校验 → 备份 → 替换 → 读回，并确认宿主 / INI / flags 前后不变，失败回滚。
- **打包**：`Development/tools/package-0xx.ps1`，底包逐文件核对、44 个 shader 变体编译、ZIP 读回校验，flags 从仓库模板复制。
- **远程 UI**：交互计划任务 `dlss5game` / `dlss5magpie` / `dlss5toggle` / `dlss5shot` / `dlss5rgp` / `dlss5toolbar` / `dlss5profiler`；Magpie 热键 **Alt+Shift+A**。
- **HIP 选项**：默认组合在 `src/native_hip_network.h` 的 HIP_FAST；诊断开关（dup / skip / memory / span probe）全部默认关。

---

## 10. 游戏适配要点

- **《剑星》**：FFX `ffxDispatch` 钩子（ReShade addon）；现走 OptiScaler 0.9.4 前置链，必须 `Dx12Upscaler=fsr31`（写 `ffx` 会静默落到 FSR2.1）；`GameUserSettings.ini` 里 AA=OFF 时 FSR 根本不创建。
- **Magpie**：输入是 8 位 sRGB 成品图，需要 `CODEC_SRGB=1`；光流在暗部会出垃圾向量，是已知限制（止血用 `MOTION_MAX_PX=64`）；包内带 XeSS FG ZeroMV。
- **浪人崛起**：XeSS 路径，运动向量符号为 −1。
- **匹诺曹的谎言**：R11G11B10 输出，需要 R11 写回 shader（0.26 修）。
- **RE9**：同一列表后面还有游戏自己的 draw（51～53 次），普通前置被安全检查拒绝。走 TheAutomatic PR5 设计的分阶段桥接 + GPL 命令列表代理，在超分前接入；曝光纹理必须传入（否则褪色）；尺寸越界要先检查、失败要回滚（0.28.1）。Xbox 版《鬼武者》用 0.26.1 后置包可用。
- **黑神话**：FSR3 静态链进 exe，未验通，已复原。
- **FIT_INPUT / FIT_LARGE**：≤1080 的小窗口 letterbox；>1080 的输入降采样到 1080 层，按亮度比调制原图。

---

## 11. 待办

- README 补三点：默认跳过 42/43/46 三块（40.66dB，清空 `DLSS5_SKIP_BLOCKS` 即全跑，约 +1ms）；ViT 自适应复用默认关、开了有损；精确流式注意力常开且逐位。
- 0.29 网盘链接等 Zero 上传后补进 README，回复 issue #6。
- 6b（wave 内归一化）画质等 Zero 看。
- 算力缺口主线：ViT 剩余缺口的限制因素、C32 余下部分的归因。
- 9060 / XT（gfx1200）至今只做了编译验证，没有实机测过。

---

## 附：history/ 文件索引（流水在本表之后）

| 文件 | 内容 |
|---|---|
| `DevHistory-full-20260923.md` | **本文压缩前的完整版**（08-31～09-23 每一刀的数字、SHA、日志路径） |
| `porting-worklog.md` | 08-31～09-08 逐块移植流水（6276 行；第 2976 行之后倒序） |
| `reverse-engineering-notes.md` | 逆向结论原始记录 |
| `CURRENT-STATE.md` | 09-07～09-10 fast 链逐刀状态（最新在上） |
| `amd-port-plan.md` / `fast-path-plan.md` / `next-steps-plan*.md` / `PLAN.md` | 各阶段计划 |
| `README.md`、`native-runtime-contract.md`、`local-patch-tool.md`、`optiscaler-intro.md` | 早期索引 / 已过时的方案 |

---

## 12. 流水（新事件追加在本节末尾，时间正序）

## 2026-09-23 16:00：DevHistory 压缩

原文 593KB（约 30 万 token，新 session 读不动）按主题重组为本文件（约 22KB）：逆向事实、当前状态、里程碑、性能演进、算力缺口认识、不要重做清单、合并教训、运维入口、游戏适配、待办。完整原文 `git mv` 到 `Development/history/DevHistory-full-20260923.md`（提交 e0824bf）。续写规则改为新事件只追加在文件最末尾。

## 2026-09-23 23:00～09-24 00:05：《卧龙 2》Alpha Demo 试装（网友反馈"用不了"）

游戏在 9070 机 `C:\Program Files (x86)\Steam\steamapps\common\Wo Long 2 Wings of Ember Alpha Demo`（Katana 引擎，Streamline 2.9 接 DLSS，自带 FSR）。装 0.29 常规 OptiScaler 包（脚本 `Development/deployments/wolong2-20260923/install.ps1`，覆盖游戏自带 libxess/libxell 时备份到 `_dlss5_backup`），逐层排查：

1. ReShade 菜单出、无 DLSS5：游戏选 DLSS 后 OptiScaler 建了 fsr31 特征，每帧 Evaluate/Dispatch 都在跑，但 addon 钩的 `amd_fidelityfx_dx12.dll::ffxDispatch` 一次没触发。改钩 `amd_fidelityfx_upscaler_dx12.dll`（26KB 的 dx12.dll 只是转发壳）仍无触发。
2. 根因（读 OptiScaler 源码 FfxApi_Proxy.h）：游戏自己先加载了 upscaler dll，OptiScaler 把它当"游戏加载的 FFX 模块"用 Detours 钩其五个导出做输入捕获，自己的派发走 Detours 跳板，不经导出入口。`[Inputs] EnableFfxInputs=false` 后钩子每帧触发，网络初始化成功（1580×888 → 900 档）。
3. 常规前置随即被自家检查拒绝：`UNSAFE: draw/dispatch after deferred upscaler in same list`——和 RE9 同类，FSR 之后同列表还有 draw。
4. 换 RE9 宿主（`-Variant re9`，不装 REFramework dinput8.dll）：`PrepareFrame: render input metadata/texture size mismatch`（游戏开着动态分辨率，纹理按最大分配）+ 宿主 300ms/2 帧稳定判定永远过不了。关掉游戏内动态分辨率后两者消失（1664×935 = 1664×935）。
5. 之后神经路径生效：画面变灰、帧率不变（60）。日志：曝光扫描 >64 个候选（RE9 定制的过滤在 Katana 上失效，曝光未识别，FP16 线性场景色按曝光 1 归一化）；`prior job not yet submitted; original SR` 反复出现（Submitted 钩子对队列/时机的假设是 RE9 的，卧龙提交路径不同，多数帧绕过）。

结论：卧龙 2 不是"装不上"，是三层都要适配：EnableFfxInputs、动态分辨率关、以及 RE9 宿主的曝光发现 + 提交观察两处 Katana 化。当前机上装的是 RE9 变体 + `LmxxfDiagnostic=off`。代码改动：`src/native_submission_order_probe.cpp` 优先钩 upscaler dll 并在 hook_status 行记模块名/导出地址、派发入口前 8 次记类型（剑星回归未做，未发包）。未记入 0.29。

## 2026-09-24 00:30：C32 转置尾部（out 并宽）null

WorkingPlan 的"C32 产出端并宽"试完：FFN 收缩 + prefix + 投影全部转置，ffn8/scratch.ex/out/pre16 的窄写并宽。逐位同，但 1080/900 六组配对全部慢 0.03ms（0.2～0.3%）。原因：残差初始化和缩放访问改成 lane=行后 LDS 读变差，投影缩放 2→16 读，chain/finish VGPR +15。开关 `HIP_C32_TRANSPOSED_TAIL` 留 0，进"不要重做"。详见 `results/c32-transposed-tail-20260924`。

## 2026-09-24 01:00：探索 1 关闭——RDNA4 没有直达 LDS 的读取

318 账本里 staging 31% 想用 `global_load_lds`（显存直落共享内存）省掉寄存器往返和 LDS 写指令。comgr 报 `__builtin_amdgcn_global_load_lds` 需要 target feature `vmem-to-lds-load-insts`，gfx1201 没有；汇编器也不认 `global_load_lds_b128`。RDNA4 上这条指令不存在（CDNA/gfx9 有），硬件没铺路。探索 1 关，改看频率账本（探索 3，`Development/HIP/experiments/clock-ledger`）。

## 2026-09-24 01:05：频率账本——功耗墙，FFN 最费电，ViT 最省电

探索 3 做完（`results/clock-ledger-20260924`）：核族 dup×8 占满一帧逐族量时钟功耗。板功耗每个配置都钉在 325～328 W，时钟随负载变：C64～C256 FFN 占满时 2.51～2.55 GHz（比基线低 8～9%），C32 低 1～1.5%，C512/C256 注意力持平，ViT 反而高 1～2%（2.78～2.85）。整网 2.75 是加权结果，峰值测试 3.1 是纯寄存器矩阵省电。318"ViT 单测 2.5 GHz"是孤立微基准的读数，要改口。新杠杆：让 FFN 核族省电能抬全帧时钟，上界 1～2%；用户侧功耗上限 +10% 值得实测。dup 开关在 flags 文件里不在环境变量（第一遍白跑，当基线重复性用了）。

## 2026-09-24 01:15：FFN 核族的电烧在全局窄写；并宽指令不省电，减少触及行数才省

FFN 占满一帧换 mh_fast 模块看时钟（`results/clock-ledger-20260924/ffn-tail`、`ffn-stores`）：串行求和、LDS 交换 + barrier 都不耗电；去掉 norm 全局写 +4% 时钟，norm 和 out 都去 +7%。prod6 把 norm 写 24 条 b8 并成 3 条 b64，时间 −2.6ms 但时钟不动——转置后每条写仍触及 16 行，功耗跟触及行数走。下一把刀（逐位）：out 从已有的 qfeature LDS 暂存整行写出，norm 按 part 暂存 4 KB 后整行写出，每行只写一次；预期 FFN 占满时钟 +7%、整帧 1～2%。

## 2026-09-24 01:30：mh_fast 全行写（HIP_FFN_LINE_STORES）——逐位，−0.6/−0.7%，prod7 候选回归通过

功耗账本指出的那把刀做完：out 从 qfeature LDS 暂存整行写出，norm 三个 part 暂存后整行写出（多一个 barrier，LDS 每组 +8.4 KB，驻留仍由 VGPR 定）。模块集 ABBA 三孪生逐位全 0，1080 −0.10/−0.10/−0.08ms，900 −0.08/−0.09/−0.09ms；FFN 占满一帧时钟 +1.2%（2526→2554 MHz）。写出字节没变所以没到"去掉写"的 +7%，省的是部分写的开销。prod7 候选（只换 mh_fast 两架构）回归：12 帧 RGB 哈希 2 序列 × 2 档全部与 prod2 基线一致，四组额外对照一致；1000 帧计时 900 12.01/12.03、1080 16.91/16.92（基线 prod2 12.62/12.72、17.80/17.88）。`results/mhfast-line-stores-20260924`、`deployments/stellar-prod7-20260924`。未装机，等用户关游戏。

## 2026-09-24 07:13：prod7 装进剑星

用户确认游戏关闭后 `stellar-prod7-20260924\install.ps1`：2 个 mh_fast 模块（gfx1200/gfx1201）哈希核对后替换，宿主/INI/flags 未动，备份 `D:\DLSSNR-Lab\stellar-prod7-20260924\backups\20260924-071340`（`-RestoreBackup` 回滚）。等用户实玩反馈。

## 2026-09-24 07:19：用户反馈 prod7

《剑星》900P 中画质拉伸 2K，常测场景稳定 60 帧（prod6 时"最快接近 60"）。prod7 通过实玩，进 0.30。

## 2026-09-24 07:30～18:30：《赛博朋克 2077》2.31 试装——三层坑，最后一层是别名瞬态资源

常规 OptiScaler 0.29 包装进 `bin\x64`（`deployments/cyberpunk-20260924/install.ps1`，覆盖游戏自带的 5 个 xess/ffx dll，备份 `_dlss5_backup`）。网友"用不了"逐层：
1. 和卧龙一样：游戏自带 FSR dll，OptiScaler 走 Detours 跳板 → `[Inputs] EnableFfxInputs=false` + 优先钩 upscaler dll 的 addon。
2. `terminal resource state not representable by FFX`：Reverse() 只认 8 种状态。补齐深度态和任意只读组合态，并把撞到的状态值写进日志（`src/native_pre_upscale.h`）。
3. **网络跑起来但画面只有色调变化。** dump 网络输入发现每帧都是同一幅"天空 + 灰地"的静止环境（第 600 帧和第 3000 帧统计四位全同，字节不同——云在动），而用户看的是街景。根因：`DLSS5_PRE_UPSCALE_ASYNC=1` 的延后提交让我们拷贝颜色纹理的命令排到游戏下一帧的早期通道之后，REDengine 的颜色缓冲是瞬态别名资源，那时那块显存装的是天空探针。剑星的颜色纹理持久，赛跑读到上一帧也看不出。**`DLSS5_PRE_UPSCALE_ASYNC=0` 后 dump 是真场景**（min 0.04 / 中位 0.17 / p99 0.64 / max 9.8，纸白 1 正好）。
中途把纸白猜成 8 是错的（那是天空探针的量级），已改回 1；顺手加了 `DLSS5_PAPER_WHITE`（Record 的门从 {0.5,1,2} 放宽到有限正数）和 `DLSS5_DUMP_FRAME`（每帧路径第 n 帧 dump 游戏颜色输入，配 DLSS5_DEBUG_DUMPS）。dump 统计脚本在 /tmp/f16stats.py 一类的临时件，结论在此。用户实机确认待做（ASYNC=0 + 纸白 1 的组合还没看过）。
教训：**同队列不等于同时序——延后提交遇到别名瞬态资源就读到别人的内容；游戏适配先关 ASYNC。**

## 2026-09-24 18:34：赛博朋克 2077 用户确认

ASYNC=0 + 纸白 1 后用户实机："材质明显差异了"。赛博朋克通过。机上 flags 已清掉 DEBUG_DUMPS/DUMP_FRAME/PAPER_WHITE，保留 EnableFfxInputs=false（OptiScaler.ini）与 DLSS5_PRE_UPSCALE_ASYNC=0；addon 是探针版（钩 upscaler dll + 状态表补齐 + 两个诊断开关），进 0.30 前要过剑星回归。

## 2026-09-24 19:10：细节量化——"只有光影"还是"有纹理"，离线一算就知道

赛博朋克那次教训：色调变了不等于网络起了作用。做了个客观指标（`/tmp` 临时脚本，方法记这儿）：输入与网络输出同尺寸，亮度进 log2(1+64L) 的显示域，减高斯低通得高频，比 RMS 与相关系数；再比梯度幅值。
- **赛博朋克（坏的那次，天空探针输入）**：σ=3 高频相关 0.9997、拉普拉斯能量比 1.04——纯色调，判"没起作用"。
- **剑星凍结菜单帧（prod7 网络输出 vs live-menu-before 输入，900 档）**：σ=1 高频 RMS +11%、梯度幅值 +13%、相关 0.887（细节是新合成的，不是拷贝）；σ=4 比 0.95/相关 0.92（中频基本保留）；低频色调变化 std 0.27（色调也变，但不只色调）。裁图 `deployments/stellar-addon030-20260924/detail-crop-in-vs-out.png`：皮肤出毛孔级纹理、布料出织纹、背景金属出颗粒，边缘有彩色微噪。
判据可复用：高频相关 >0.99 且能量比 ≈1 = 只改了色调；相关 <0.95 且 σ=1 能量比 >1.05 = 有新细节。用户实机（19:06）：双钩 addon 在剑星画面/60 帧照旧。
- **赛博朋克第 3000 帧（ASYNC=0 后的真场景，中央裁 1296×720 离线跑 prod7 900 档）**：σ=1 高频比 1.001、相关 0.973；σ=2/4 比 1.03/1.04；梯度幅值 +13%。比剑星温和：它的输入本身已经很锐（高频 RMS 0.152 对剑星 0.131），网络主要是把已有的划痕/磨损纹理强化、边缘高光提亮，不像剑星那样在光滑皮肤上合成新纹理。裁图 `deployments/cyberpunk-20260924/detail-crop-in-vs-out.png`。用户主观"材质明显差异"与此一致。

## 2026-09-24 19:16：剑星双钩 addon 帧率（用户）

900P 拉 2K 最简单场景 60～61 帧，经 Splashtop 远程测（远程 UI 约吃 1～2 帧，本机应 61～63）。双钩 addon（c7f68e60…）在剑星画面/帧率与 prod7 一致，剑星侧通过。赛博朋克帧率待用户报。

## 2026-09-24 19:29：赛博朋克帧率（用户）

低画质 900P 拉 2K 约 50～51 帧（Splashtop 远程）。用户主观：材质有差异但"不够真实"；屏幕上黄色分辨率/帧率字样在 2077 里没显示。

## 2026-09-24 19:40：prod7 内核装进 RE9

RE9 目录里的内核比 prod6 还旧（0.28.1 那版，c32/mh_fast 哈希都对不上）。runtime 从 HIP\gfx1201 加载（LUID 选子目录），SHA256SUMS 只查文件名。`deployments/re9-prod7-20260924/install.ps1`：两架构各覆盖生产模块（10 个换掉，参考/实验模块不动），备份 `D:\DLSSNR-Lab\re9-prod7-20260924\backup`（-Restore）。gfx1201 mh_fast 98faa6d4、gfx1200 36ad568f = prod7。等用户看效果。

## 2026-09-24 19:50：RE9 装 prod7 后用户"绝对只是亮度变化"——抓帧量化说不是

用 RE9 宿主的 capture-colour.request（runtime 从 _storage_ 加载，请求放 _storage_）抓同帧：input RGB9E5 1512×848、proxy/neural 1600×900 FP16、result FP16。
- 网络域 proxy→neural：细纹理能量比 1.03、相关 0.979、**梯度幅值 +19.5%**。
- 游戏域 input→result：能量比 1.08/1.11/1.13（σ=1/2/4）、相关 0.99/0.986/0.982、梯度 +19%；平均亮度 4.108→4.077（几乎不变）。
判据：色调-only 是相关 0.9997、比 1.0、梯度 1.0；RE9 明显不是。裁图 `deployments/re9-prod7-20260924/detail-crop-in-vs-out.png`：面板缝、划痕、黑色金属边缘都更硬。
另外 prod7 与 0.28.1 内核逐位同（回归对 prod2 基线 12 帧哈希全同），换内核不可能改画面，只可能改速度；用户印象里的"之前不一样"不是内核造成的。发出去的 0.29 REFramework 包（prod6 内核 + fitlarge runtime）同理不受影响。本机 D: 上 0.29 包文件夹和 zip 已不在（用户上传后删了），无法重新哈希。

## 2026-09-24 20:00～20:50：强度外推试看、Google Drive 链接、网友"统一宿主"补丁审查

- 用户要看"最高强度"：`DLSS5_STRENGTH` 上限放到 3（>1 沿 lerp 外推，纯诊断），剑星/2077 flags 临时写 2,1；用户看完 21:07 已删回默认。
- 0.29 三包补了 Google Drive 镜像（给没有中国手机号的用户），README 两处链接；以后发布 = 夸克 + Google Drive。
- git：用户定"只推 297，别动外层 ai-theorys-study"。
- 网友的 OptiScaler 通用宿主补丁（统一 RE9 与常规包）审完，归档 `Development/RE9/presr/contrib/generic-host-20260924/REVIEW.md`：查询记账（切点无未闭合查询即可切分）与提前包裹（返回地址判断游戏 exe 建列表）两处可用；backend 补丁是我们 prepare-host.py 旧快照的翻版且缺曝光 ABI v2 两行；runtime 编译脚本不打我们的 runtime 补丁（退回 0.26 时代）；宿主 dxgi.dll 需 MSVC 未提；无测试证据。等用户问到网友在哪个游戏跑通、帧率多少再定要不要合进 prepare-host 实测。

## 2026-09-24 21:10～21:50：2077 三方对比（默认 / OP / Magpie 0.29）——红偏来自颜色转移，改成按 exe 查表 1,0

用户同机位截四张（机位微差，逐像素对不上，看全局统计 + 等倍裁片；图在 `deployments/addon030-strength-20260924/`）：

| | 平均 R/G/B | 高通细节 RMS（σ=2，log 亮度） |
|---|---|---|
| 默认 FSR（F6 关） | .107/.112/.059 | 0.159 |
| OP 1,1（847p 前置） | .122/.094/.049 | 0.193（+22%） |
| OP 1,0（只转亮度） | .120/.121/.072 | 0.189（+19%） |
| Magpie 0.29（1080p 后置，OSD 30 帧 33 ms） | .105/.111/.055 | 0.212（+34%） |

- 第一轮误判：先拿到的 op/magpie 两张机位差太多，看成"OP 动得轻"；补了默认那张才看清：OP 1,1 不是轻，是**色相转了方向**——R +14%、G −16%，绿色霓虹环境光压成灰褐；Magpie 和默认色调几乎一样，只加细节。
- 原因：前置路线把色调映射**之前**的线性缓冲交给网络，解码 `Hue(neural×ratio, neural)` 在线性域取神经色相，再过 2077 的 tonemapper + LUT，色相就跑了；Magpie 吃的是 sRGB 成品，LUT 已定型。
- 只转亮度（1,0）：色相比例回到游戏自己的，细节增益基本没丢（+19% 对 +22%），脸/报纸/红衣服都比默认清楚。
- 落地：`native_game_codec.h` `LegacyParameters` 里 `DLSS5_STRENGTH` 缺省或 `auto` → 按 exe 查表（Cyberpunk2077.exe → 1,0，其他 1,1），写 `event=strength` 到 oneshot 日志；模板 `hip-game-flags.txt` 加 `DLSS5_STRENGTH=auto`，CONFIGURATION.md 一行。addon a569ed6f…（`deployments/addon030-strength-20260924`，build-addon-oneclick.sh --hip），21:50 两游戏都关着，已装进剑星和 2077（backup-stellar / backup-cyberpunk，`install.ps1 -Restore`），两处 flags 的显式 STRENGTH 行删掉由表决定。剑星行为不变（1,1）。
- 细节上限：Magpie 在 1080p 上跑网络所以细节比 OP 多一截，但 30 帧对 51 帧；这是前置路线用 847p 换帧率的结构代价，不是 bug。
- RE9 宿主路线（LmxxfNrRuntime.cpp 自己读 `DLSS5_STRENGTH`，上限 1）不受影响；RE9 是后置 sRGB 域，色相问题不适用。

## 2026-09-24 23:00～25 01:30：launch 尾巴——双流死路，同流任意序 + tile 旗子成刀（900 −1.6%）

主线第 4 条。先量驱动（`HIP/experiments/stream-overlap`）：两条 stream 在这块 Windows HIP 上**完全不并发**（只有一条硬件队列，`GPU_MAX_HW_QUEUES` 无效），跨流事件一对 110～180 μs；同流 `hipExtModuleLaunchKernel` + `hipExtAnyOrderLaunch`（去 AQL barrier 位）能让下一个 launch 在上一个收尾时派发（2 wave/SIMD 时每 launch 198 → 31 μs）。第一版 spin 核用 `readsteadycounter` 计时，那条 `s_sendmsg_rtn` 全 GPU 串行，量出来全是消息拥塞——换成 `SHADER_CYCLES` + `s_sleep` 才对。
任意序没有"部分依赖"，只能把依赖搬进核里：土法 programmatic dependent launch（`HIP/experiments/pdl-chain`，`results/pdl-chain-20260925`）——C64/C128/C256 六条链上 FFN/QKV 核与窗口注意力核各发 `_pdl` 孪生，入口按 token 坐标等上游 tile 的计数器（FFN 组等上一块注意力的 ≤6 个窗口，注意力组等本块 FFN 的 ≤8 个 tile），出口每 wave `fence(release)` 后 +1；host 链头普通提交、其余任意序，计数器按（核种、通道、格子宽高）各一份、永不清零、目标为累计 wave 数；最近几块张量攥住不还 pool。逐位：18 个槽 2880 帧零差异。
拆账（1080）：协议纯成本 +0.25～0.29 ms（发旗 0.10，等旗 0.15～0.19：组开头一次 L2 往返 + barrier，没法和核开头重叠），调度捡回 0.23（正好是 launch-occupancy 预测的尾巴）；组屏障发旗版净零，改每 wave 发计数器 + 去掉 per-group acquire 后净 −0.1（−0.6%）；**900：11.74 → 11.55，−0.18 ms，−1.6%**，三次重跑 −0.16～−0.19。只开 FFN 或只开注意力都是零，两头要一起。
坑：(1) 环形槽位混用不同尺寸格子 → 累计目标追不上 → 死锁一次；(2) helper 里加空指针提前返回那版在任意序下三跑三报 `hipErrorLaunchFailure`，普通提交正常，撤掉后两跑两过，原因未明；(3) 时钟随功耗漂，只看相邻 A/B。
生产化：两份 hip 源加 `HIP_PDL_KERNELS` 孪生（原核不动）、host `opt.pdl`（`DLSS5_HIP_PDL`，模板 =1，Magpie 模板同）、插件重编 5be18ac3…；`deployments/stellar-prod8-20260925`（build/regression/payload/install）。regression-prod8（01:02）：900/1080 各两序列 12 帧哈希对 prod2 逐位全同；1000 帧 ABBA 对 prod2 基线：900 −0.80 ms（−6.3%，prod7 同口径 −0.65/−5.1%，即 prod8 比 prod7 约 −1.2%），1080 −1.02 ms（−5.7%，prod7 −0.92/−5.2%，约 −0.5%）。日志 `deployments/stellar-prod8-20260925/regression-prod8.log`。**等用户关剑星装机。**
