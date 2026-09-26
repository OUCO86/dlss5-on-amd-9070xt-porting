# C32 post70 输入实验（2026-09-25，Yami）

## 数据流审计

当前 HIP 生产路径中，mapped 输入并非 HLSL 编码器直接生成：

| 消费者 | 生产者 | 当前格式/用途 |
|---|---|---|
| block1 half_mapped | block0 prefix_finish_main8 的 down 输出 | 半分辨率、行主序、f32 C32；block1 shift=0 |
| block66 half_mapped | decoder_project2x_h16w 的 oc=32 输出 | 半分辨率、行主序、f32 C32；shift=0 |
| post70 low | block69 chain_finish 的 main 输出 | 半分辨率、行主序、f32 C32；每像素被 2×2 上采样复用 |
| post70 skip | block0 prefix_finish_main8 的 main8 输出 | 全分辨率、行主序、FP8 C32；贯穿整网保留 |

位置：`hip/c32_fused_ffn_attention.hip` 的 mapped staging / Finish；`Development/HIP/hip_reference_network.h` 的 C32Chain / Up / RunGraph。

9 月 23 日的 `HIP_C32_BYTE_CHAIN` 分支已把 mapped/post 从每 lane 16 次 b32 读取改为 4 次 b128。旧 WorkingPlan“十六行散读，改 tile 后读等待砍半”的收益推断不能照用。每 token 的 32 个 f32 本来就连续；改 token 行序不保证减少当前读取触及的缓存行。

完整 tile 化会牵涉多个生产者、shift/padding 与存活期，先试更小的 post 低分辨率重复读取消除。

## 本轮候选

一个 wave 管 16 token = 两行各 8 像素；post 的 sy=0/4、处理高度为偶数时，两行对同一低分辨率行取数。staging 的 k=2/3 与 k=0/1 对应相同的 low 地址、通道和有效性。

候选将 low 的后两次 b128 读取改为前两次的寄存器复用。skip 仍各读各的；Hrtz、FP8 转换、残差和矩阵运算不改。奇数 sy/height 回落原读取，避免把几何假设偷偷推广。

只产生 `c32_post_merge_head_half_reuse` 实验导出，生产源不动。另有同体异名 `_control`，检查代码放置/编译带来的对照差异。可能失败原因：编译器已消除冗余、缓存已消化重复请求、寄存器延长存活反而损失驻留。源码少两次读取不等于 ISA 少两次，更不等于变快。

后续变体沿用同一文件：mode 3 `_reuse_even` 将偶数几何条件提升到 host 检查，避免核内分支；mode 4 `_half_low` 将 block69 的 main 写成 FP16，post70 对应读取 FP16 再转回 f32。block69 写出的 `F(float(scratch.ex[...]))` 已在 FP8 格点上，FP16 可精确承载，不改求和或舍入顺序。mode 4 同时选择 chain_finish 与 post70 两个孪生核，block4 的 chain_finish_dcrop 不动，分配容量暂不缩小。host 拒绝非生产链配置或跳过 block69，防止不配套的生产者/消费者混用。

## 执行与验收

1. 本机 `python3 prepare.py` 生成 `/tmp/c32-post-input`，`python3 check-addresses.py` 验证边缘/内部 token 地址等价。
2. 用 MinGW 编译生成的 `network.cpp` 为 `network.exe`（`-O2 -std=c++17 -static -I /tmp/c32-post-input`）。将输出和三个 PowerShell 脚本放到靶机 `D:\DLSSNR-Lab\hip-backend\c32-post-input`。
3. 靶机 `start.ps1`：检查空闲，从 prod8 模块集复制独立实验目录，编译 gfx1201 实验模块，再跑 900/1080。不会安装到游戏。
4. 当前 host 选项从生产源提取，强制 PDL=1、graph/adaptive=0、dup 关。每轮先跑生产/同体异名 ABBA，再跑生产/复用 ABBA，默认各三轮、每槽 160 帧。只在计时段外读回；槽首尾 RGB 对现有 expected.f32 逐位比较，确认 post 每帧确实调用一次。
5. `results-900/slots.csv`、`results-1080/slots.csv` 保存整网帧时。基线也是本次从当前源码重编的原核；编译后须核对其 ISA/资源用量与 prod8 C32，检查 `_control` 与原核是否只有符号差异。结果不显著则归档，不上生产。

`start.ps1 -Candidates 1,3 -Label even` 只跑 control 和偶数特化；`-Candidates 1,4 -Label half` 跑 FP16 边界。`analyze.py <结果目录>` 汇总 ABBA；`inspect.py <prod8.hsaco> <实验.hsaco> <实验.hsaco.s>` 检查原核二进制未变和 staging 指令。

本轮是固定输入、无 history 的候选筛选；通过后再做生产多帧/重置/历史回归与双架构构建。实测结论见 `Development/results/c32-post-input-20260925/README.md`，不要把源码改动当提速结果。
