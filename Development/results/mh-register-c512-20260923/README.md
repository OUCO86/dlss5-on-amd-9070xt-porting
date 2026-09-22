# C512 注意力核（mh_attention_fused_fp8_out）ex/prob 寄存器化：逐位同，无收益（2026-09-23，Hikari）

同 mh-register-attention 的改法用在 C512 的 4-wave 注意力核：ex[64×66]（8.4KB）删除，分数/行和 WMMA 对调，prob 留寄存器，3 个同步剩 1 个，LDS 15.4→7KB。基线 = prod5。

整网 ABBA 三份（每测试 8 槽 160 帧，逐位同）：1080 −0.014 / +0.008 / +0.005ms，900 −0.012 / −0.009 / −0.012ms，全部交叠。

结论：这个核不受 LDS 驻留限制（原本每 CU 已能放 4 组），去掉 ex 和两个 barrier 都没换来时间。与 C64～C256 函数体形成对照：**同一改法赚不赚取决于该核的驻留被什么卡住**。不采用。证据 r1/。工具 HIP/experiments/mh-register-c512。
