# ffn_fused wave 内 QKV 归一化（1b，非逐位），−0.18/−0.14ms 再加于转置之上（2026-09-23，Hikari）

**第一处放弃逐位的改动。** 在 [尾段转置](../mhfast-transposed-qkv-20260923/README.md) 之上：part 0/1 各由 C/32 个 wave 承担，每 wave 持一个 head 的 32 列（两个列 tile × 16 k = 32 WMMA），part 2 仍每 wave 16 列（16 WMMA），每 wave 48 WMMA 不变。转置布局下一行的 32 列落在 lane l 与 l^16 各两个 tile：平方和 = lane 内 16 项顺序求和 + 一次 `ds_bpermute` 相加，`rsqrt`、scale、norm 字节全在寄存器里出，没有 storage.raw 往返、没有两个 barrier、没有 128 线程串行循环。**求和从 32 项顺序变为两个 16 项部分和相加**——只在 rsqrt 之前重结合，其余每一步（WMMA 顺序、q8 舍入）不变。

整网 ABBA（模块集 host，基线 prod5 未转置，三份相同集合 = 三份复现）：

| 档 | 总差（转置 + wave 归一化） | 减去转置 | 输出差异元素 |
|---|---:|---:|---:|
| 1080 | −0.460 / −0.467 / −0.451 ms（−2.7%） | **−0.17～−0.19（1.1%）** | 23.4M |
| 900 | −0.351 / −0.347 / −0.361 ms（−2.9%） | **−0.13～−0.15（1.1%）** | 15.4M |

槽全部不交叠，核心频率两侧相同。上界（消融 2）1.5%，拿到 1.1%。

差异量级：整网原始 FP32 输出大约每三个元素有一个不同，这是 fp8 归一化偶发单位翻转经十几层放大的结果，不能直接读成画质。画质看 [prod6b 回归](../../deployments/stellar-prod6-20260923/) 的 12 帧 RGB 逐像素差（rgbdiff.py：max / mean / >1/255 比例 / PSNR）和用户在游戏里的判断。**未进生产源默认值**：`HIP_FFN_WAVE_NORM` 默认 0，prod6 候选不含它；6b 模块只用于差异研究。

证据：1080/、900/ 下 network.csv、run.log、telemetry.log；summary.txt；console.log。工具 HIP/experiments/mhfast-wave-norm。
