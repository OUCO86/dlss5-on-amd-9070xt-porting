# stellar-prod6 候选（2026-09-23，Hikari）—— 攒着，未装

内容（全部逐位，相对装机版 prod2）：prod5（C32 字节链 + 向量化 staging、mh_fused c64～c256 注意力寄存器化）+ C32 in16 别名到 Scratch（`HIP_C32_IN16_ALIAS`）+ ffn_fused 尾段转置（`HIP_FFN_TRANSPOSED_TAIL`）。6 个文件：c32 / mh_fused / mh_fast × gfx1200 / gfx1201（mh_fused 与 prod5 相同）。

回归（regression-prod6.log）：12 帧 RGB hash 两序列两档全同；额外控制组（720-motion、900-history、900-float-in、900-float-feature）全同；1000 帧计时（帧 ≥200 均值，槽 0/3 基线、1/2 候选）：

| 档 | 基线 | 候选 | Δ |
|---|---:|---:|---:|
| 900 | 12.624 / 12.691 | 12.107 / 12.134 | **−0.54 ms（−4.3%）** |
| 1080 | 17.822 / 17.898 | 17.057 / 17.072 | **−0.80 ms（−4.5%）** |

安装：剑星关着游戏时跑 `D:\DLSSNR-Lab\stellar-prod6-20260923\install.ps1`（hash 校验、备份、失败自动回滚；`-RestoreBackup <备份目录>` 回退）。

## 6b（非逐位，仅研究，不在 payload 里）

prod6 + `HIP_FFN_WAVE_NORM`（wave 内 QKV 归一化）。模块 `network-fixed-shapes\prod6b-modules\multihead-fast-padded-wave-packed.hsaco`（gfx1201 4d1ffa75…）。regression-prod6b：计时 900 12.537/12.556 → 11.854/11.881（**−0.68 ms，−5.4%**），1080 17.703/17.732 → 16.728/16.736（**−0.99 ms，−5.6%**）。12 帧 RGB 逐像素差（rgbdiff.py，值域 0～1）：

| 档/序列 | max | mean | 差异像素 | >1/255 | PSNR |
|---|---:|---:|---:|---:|---:|
| 900 seq0 | 0.172 | 4.3e-4 | 68% | 1.39% | 57.8 dB |
| 900 seq1 | 0.19 | 4.4e-4 | 68% | 1.47% | 57.2～58.0 |
| 1080 seq0 | 0.119 | 4.3e-4 | 70% | 1.37% | 58.7 |
| 1080 seq1 | 0.16～0.18 | 4.2e-4 | 70% | 1.2～1.4% | 58.4～59.1 |

读法：平均差 4e-4（约 0.1/255），PSNR 58 dB 以上，1.4% 像素差超过一个 8 位灰阶，个别像素（边缘）差到 0.17。数值上属于"看不出"的量级，但 max 那些点是不是会闪，要在游戏里看。装 6b 需要另做 payload（只换 gfx1201 mh_fast，gfx1200 未编）。
