# 直接读取残差的ISA对照

对照已验证的c256-projection-pairs内核汇编与mh-exact-feature候选；这些attention入口在后续FFN/QKV模块优化中未改变。仅静态资源及指令统计，不是执行次数/周期测量。

| 入口 | VGPR 原→候选 | SGPR 原→候选 | private bytes 原→候选 |
|---|---:|---:|---:|
| c64_attention_project | 94 → 82 | 30 → 53 | 0 → 0 |
| c128_attention_project | 118 → 106 | 30 → 53 | 0 → 0 |
| c256_attention_project | 152 → 133 | 42 → 43 | 0 → 0 |

C64片段的部分静态指令计数：

| 指令 | 原版 | 候选 |
|---|---:|---:|
| `v_cvt_pk_fp8_f32` | 102 | 81 |
| `v_cvt_f32_fp8_e32` | 54 | 33 |
| `v_fma_f32` | 40 | 24 |
| `v_fmac_f32_e32` | 29 | 28 |
| `v_dual_fmac_f32` | 38 | 3 |
| `global_load_b32` | 27 | 18 |
| `global_load_b64` | 12 | 12 |

基线ABBA19.340/19.337ms，候选19.860/19.822ms；最终图像hash一致。候选确实减少转换及VGPR，但SGPR和指令安排同时变化。双发射FMA数量减少提示调度变化，不能单凭静态数量断言它解释全部性能退化；分支路径/循环执行次数与实际调度未测。维持原实现。
