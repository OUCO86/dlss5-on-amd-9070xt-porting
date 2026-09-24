# launch 尾巴：同流任意序 + tile 旗子（土法 programmatic dependent launch）（2026-09-25，Hikari）

工作计划第 4 条"launch 尾巴用两条流盖住"的落地。先量清这块驱动上能用什么，再改。工具 `HIP/experiments/stream-overlap`（微基准）和 `HIP/experiments/pdl-chain`（整网 ABBA，逐位强制）。

## 一、驱动上什么能并发（stream-overlap，spin 核，9070 XT，Windows HIP 7.0）

spin 核第一版拿 `__builtin_readsteadycounter`（`s_sendmsg_rtn REALTIME`）计时，那条消息全 GPU 串行化，200 μs 的等待两次轮询就到期、核的耗时随 wave 数线性涨——量的是消息拥塞不是并发。改成每 wave 本地的 `SHADER_CYCLES`（`s_getreg`）+ `s_sleep` 后才可用。

| 量什么 | 结果 |
|---|---|
| 同流 launch 间隙（空核连发） | 1～3 μs/launch |
| 跨流事件对（record + wait，DisableTiming） | **110～180 μs/对** |
| 两条 stream 各发独立核 | **完全不并发**（32 个 K=32 链：每 launch 198 μs，与单流串行一样；`GPU_MAX_HW_QUEUES=4` 也一样）——这驱动实际只有一条硬件队列 |
| 同流 `hipExtModuleLaunchKernel` + `hipExtAnyOrderLaunch`（去 AQL barrier 位） | **真并发**：2 wave/SIMD 时 198 → 31 μs/launch，8 wave/SIMD 时 → 93 |
| 任意序 + 核内旗子等待的依赖链（check_pdl，32 级，每级等上一级两个组的旗子并读它们写的数据） | 0 处错（release/acquire 路径把生产者数据带过来了）；组数刚超过一轮时（300 组 / 16 wave 槽位）每 launch 57%；组数不足一轮时 90～120%（等待的组占着槽位轮询） |

结论：双流路线死（两条 stream 不并发、事件一对 110 μs）；能用的只有同流任意序，且因为它没有"部分依赖"（barrier 位要么等全部前序、要么谁也不等），依赖只能搬进核里做——每个 tile 一面旗子。

## 二、整网落地（pdl-chain）

C64/C128/C256 六条链（编码 3 + 解码 3）上的 FFN/QKV 核与窗口注意力核各发一个 `_pdl` 孪生（prod7 源码加 helper，原核 ISA 不动）：

- FFN 组（格子上 16 个连续 token）入口：lane 0～15 各查自己 token 在**上一块注意力格子**里落进哪个窗口（图像坐标 + 上一格子的 pad 与宽度），轮询该窗口旗子 ≥ 目标；`s_barrier`；不做 per-group acquire（见下）。出口：每个 wave `fence(release, agent)` 后 lane 0 对本 tile 计数器 +1。
- 注意力组（一个 8×8 窗口）入口：lane 0～63 各查自己 token 所在 FFN tile（`raster(win,tok)/16`）的计数器；出口同上，对本窗口计数器 +1。
- host：同流，链头 FFN 普通提交（等 pool），其余全部 `hipExtAnyOrderLaunch`。计数器按（核种、通道、格子宽高）各一份，永不清零，目标 = 该份累计使用次数 × 每组 wave 数（第一版环形复用把不同尺寸格子混在一份里，早先没用过的 tile 计数永远追不上，死锁一次）。最近几块的张量攥住不还 pool（任意序下上一块可能还在读）。
- 逐位：每槽 160 帧全和 expected.f32 比，全部 0 差（1080 共 11 个槽、900 共 7 个槽，含三次稳定性重跑）。

### 拆账（1080，ms/帧，A/B 各 4 槽的中位）

| 模式 | 相对普通提交 |
|---|---|
| `_pdl` 核 + 普通提交（协议纯成本） | **+0.25～0.29** |
| 　其中：只发旗子不等（PDL_NO_WAIT 变体） | +0.10 |
| 　其中：等旗子（差值） | +0.15～0.19 |
| 任意序只开 FFN | +0.10 |
| 任意序只开注意力 | +0.10 |
| 任意序两头都开（组屏障发旗版） | ≈0 |
| 去掉 per-group acquire（`gl0/gl1` 失效会把同 CU 其他驻留组的权重踢出 L0，但量下来不是主项） | 等待成本没变 |
| **两头都开，每 wave 发计数器，无 acquire** | **−0.08～−0.15（−0.6%）** |

调度那半确实把预测的 0.23 ms 尾巴（launch-occupancy 账）捡回来了，但协议自己吃掉一多半：等待 = 组一开头一次 L2 往返（旗子是 agent 域原子读，绕过 L0）+ 一次 `s_barrier`，每组 1～2 μs，对 10～20 μs 的组是 5～10%。发旗 = `vscnt(0)` 等本 wave 的写落到 L2。

### 900（用户实玩档）

| 模式 | ms/帧 |
|---|---|
| 普通提交 | 11.70 / 11.74 / 11.76 / 11.76 |
| 任意序两头都开 | 11.53 / 11.55 / 11.58 / 11.57 |
| 只开 FFN | ≈0 |
| 只开注意力 | ≈0 |

**−0.18 ms，−1.6%**，逐位。900 比 1080 赚得多是因为 launch 更小、尾巴占比更大（launch-occupancy：c256 注意力尾巴 900 是 37%、1080 是 25%）。

## 三、还能挤的

1. 等待的那次 L2 往返没法和核的开头重叠（FFN/注意力开头就读生产者数据）；能省的只剩 `s_barrier`。
2. C512 链（13 块 × 7 个 20 多 μs 的小 launch）和 ViT 的 launch 边界最密，同一套旗子机制搬过去（split_mix/split_ffn/projection/qkv_norm 都是逐 token，注意力是窗口）——但那 7 个核各不相同，要分别接。
3. 跨链：Down/Up/pool 核也接旗子，链头就不必普通提交。

## 四、生产化路线

host 补丁进 `Development/HIP/hip_reference_network.h`（`DLSS5_HIP_PDL=1` 开，默认关）；两份 hip 源加 helper 与 `_pdl` 孪生（宏 `HIP_PDL_KERNELS`，原核 ISA 不变，模块哈希变）；回归用 regression-prod7.ps1 同款 12 帧哈希比对；装剑星实测帧率。

## 限制

- 任意序下旗子 `>=` 累计目标的正确性依赖"同一份计数器相邻两次使用之间至少隔 4 个 launch，而 CP 按包序派发组"这条经验论证，不是硬保证；逐位回归通过 18 个槽 2880 帧，装机后仍要看。
- 曾出现一版核（发旗/等旗 helper 加了空指针提前返回）在任意序下三跑三次 `hipErrorLaunchFailure`，普通提交下正常；撤掉后两跑两过。没查到原因，记着。
- 时钟随功耗漂（A 槽一轮内 16.47 → 16.75），只看相邻 A/B 差。
