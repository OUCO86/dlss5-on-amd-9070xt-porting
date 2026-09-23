# 当前工作计划（覆盖式，不续写；最后更新 2026-09-23 09:55，Hikari）

> 这个文件只记"现在打算做什么、等什么"，每次直接覆盖。已完成的事进 DevHistory.md，不在这里重复。

## 状态

- 算力缺口研究：launch 级、核内级、请求级三层账已闭合，逐位约束下的手法穷尽。整网累计约 −5%：−2.7% 已装剑星（fence + 折叠 FFN），−2.2% 攒在 prod5 候选（字节链 + mh 注意力寄存器化），−0.5% 在生产源未编（C32 in16 别名，`HIP_C32_IN16_ALIAS`）。
- 研究结论（写进 318）：必要损失约 25～30%；可回收的已回收；两条规则——并宽只在 lane 间仍连续时有效，驻留只在它是瓶颈时值钱。

## 待办（按顺序）

1. **放弃逐位的第一处：ffn_fused 的 QKV 归一化交换**（消融上界 1.8%，results/mhfast-tail-ablate-20260923）。做法分两步：
   - 1a（逐位）：QKV WMMA 操作数对调得转置结果，lane 持一行 8 列——storage.raw 写/inverse 读/norm 写/残差读全部并宽，串行求和顺序不变。估 ≤0.1ms，先验证布局。
   - 1b（非逐位）：part 0/1 各 8 个 wave 每 wave 持一个 head 的 32 列，平方和 wave 内完成（4 个 8 项部分和重结合），去掉两个 barrier 和 LDS 往返。编候选装机由用户看画质。
   - 不做注意力行和（寄存器版只剩 4 条 WMMA）。
2. **prod6 候选**：把 prod5 + in16 别名一起编（gfx1200/gfx1201），跑 regression-prod6.ps1，出 install.ps1 + payload.json。攒着，用户说装再装。
3. **318 成稿**：素材在文末"待整理材料"和各时间点补记；成稿前重新检索文献（Roofline 2009、Hierarchical Roofline、微基准反推、Hong & Kim 2009、PaLM MFU），重排结构。结尾句已备。
4. host 侧小改等 addon 重编时顺带：宽权重片段（−0.03ms）、小 launch 合并（未量）。

## 不做 / 已关

CU 模式逐核、C32/C512/ViT 注意力寄存器化、split_projection 转置尾声、BatchNorm 合并 barrier、ffn_fused VGPR 封 96、注意力残差读提前（寄存器版已盖住延迟）、c256 注意力尾巴（结构税：投影要 8 头 AV，host 链上无并发兄弟）。

## 机器与流程

9070 机器 `amd9070`，工作根 `D:\DLSSNR-Lab\hip-backend\`；编译 `dual-arch-src\rtc_compile.exe <out> <src> comgr gfx1201`；跑前 `check-idle.ps1`；长 ssh 用后台任务。实验模板：kernel 后缀 ABBA（c32-lds-alias）、模块集 ABBA（mhfast-vgpr-cap）、核内打点（launch-occupancy）。
