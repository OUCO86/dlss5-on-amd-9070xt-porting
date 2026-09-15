# MH AV pair：gfx1201汇编对照

比较当前源码与归档AV-pair候选，二者均用HIP_ISA_HALF=1、COMGR编译。只截取mh_attention_fused_fp8_out函数。以下为静态指令数量，不是动态执行次数或周期。

| 指标 | 当前 | AV pair |
|---|---:|---:|
| `ds_load_2addr_b32` | 20 | 20 |
| `ds_load_b96` | 1 | 1 |
| `ds_load_u16` | 33 | 33 |
| `ds_load_u16_d16_hi` | 1 | 1 |
| `ds_load_u8` | 64 | 64 |
| `ds_store_b16` | 32 | 32 |
| `ds_store_b32` | 1 | 1 |
| `ds_store_b8` | 32 | 32 |
| `s_barrier_signal` | 3 | 3 |
| `s_barrier_wait` | 3 | 3 |
| `v_wmma_f32_16x16x16_f16` | 4 | 4 |
| `v_wmma_f32_16x16x16_fp8_fp8` | 16 | 16 |
| VGPR | 103 | 104 |
| SGPR | 20 | 20 |
| LDS bytes | 15360 | 15360 |
| private segment bytes | 0 | 0 |
| VGPR/SGPR spill count | 0/0 | 0/0 |

LDS读取和矩阵指令数量未减少，因此源码共用概率读取没有落实为该指标上的节省。VGPR差1不能直接证明占用率变化或导致变慢，需分配粒度/驻留证据。实际ABBA为当前22.792/22.812ms、候选22.862/22.831ms；维持当前实现。

AV阶段64条ds_load_u8仍值得定位，但以前V转置（mh-transpose-v.patch）已测无收益；不能重复该方案并宣称新发现。
