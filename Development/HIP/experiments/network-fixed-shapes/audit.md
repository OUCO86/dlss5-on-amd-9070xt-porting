# 当前默认900P路径：234次调用的固定尺寸审计

依据已验证的调用拓扑CSV，静态审计范围为当前默认路径，不声称覆盖所有可选flag。

| 入口 | 次数 | 本轮处理 |
|---|---:|---|
| c32_fast_ffn_attention_fused_half_prefix_finish_main8 | 1 | 矩阵维度/循环界限已固定；不盲目重做全局展开 |
| c32_fast_ffn_attention_fused_half_mapped | 2 | 矩阵维度/循环界限已固定；不盲目重做全局展开 |
| c32_fast_ffn_attention_fused_half_chain | 4 | 矩阵维度/循环界限已固定；不盲目重做全局展开 |
| c32_fast_ffn_attention_fused_half_chain_finish_dcrop | 1 | 矩阵维度/循环界限已固定；不盲目重做全局展开 |
| mh_pool_project_production_h16w | 2 | 候选8：C32常量 |
| mh_ffn_fused_c64_project_g128_qkv_fb | 1 | 通道模板/常量已固定 |
| c64_attention_project_fb_bout_diag | 6 | 通道模板/常量已固定 |
| mh_ffn_fused_c64_project_mapped_g128_qkv_bytein_fb | 6 | 通道模板/常量已固定 |
| c64_attention_project_fb_diag | 2 | 通道模板/常量已固定 |
| mh_pool_project_group_c64 | 1 | 通道模板/常量已固定 |
| mh_ffn_fused_c128_project_g128_qkv_fb | 1 | 通道模板/常量已固定 |
| c128_attention_project_fb_bout_diag | 10 | 通道模板/常量已固定 |
| mh_ffn_fused_c128_project_mapped_g128_qkv_bytein_fb | 9 | 通道模板/常量已固定 |
| mh_ffn_fused_c128_project_g128_qkv_bytein_fb | 2 | 通道模板/常量已固定 |
| c128_attention_project_fb_diag | 2 | 通道模板/常量已固定 |
| mh_pool_project_group_c128 | 1 | 通道模板/常量已固定 |
| mh_ffn_fused_c256_frag_project_mapped_g128_qkv_fb | 1 | 通道模板/常量已固定 |
| c256_attention_project_fb_bout_diag | 14 | 通道模板/常量已固定 |
| mh_ffn_fused_c256_frag_project_mapped_g128_qkv_bytein_fb | 15 | 通道模板/常量已固定 |
| c256_attention_project_fb_diag | 2 | 通道模板/常量已固定 |
| mh_pool_project_group_c256 | 1 | 通道模板/常量已固定 |
| mh_shift_pack | 13 | 候选32：C512常量，优化寻址 |
| split_mix_blocked_h16w | 13 | C512尺寸已固定，剩余动态项主要为位置/数量 |
| split_ffn_fused_fp8_t8 | 13 | C512尺寸已固定，剩余动态项主要为位置/数量 |
| split_projection_frag | 13 | C512尺寸已固定，剩余动态项主要为位置/数量 |
| mh_qkv_normalize_frag_c512 | 13 | C512尺寸已固定，剩余动态项主要为位置/数量 |
| mh_attention_fused_fp8_out | 13 | 候选16：C512常量 |
| mh_attention_project_frag_c512 | 13 | C512尺寸已固定，剩余动态项主要为位置/数量 |
| mh_pool | 1 | 候选32：C512常量，优化寻址 |
| vit_gather | 2 | 搬运/打包，无动态K矩阵循环；未改 |
| vit_pack_input | 8 | 搬运/打包，无动态K矩阵循环；未改 |
| vit_expand_blocked_fp8_frag_bytein | 8 | 候选1：K1024/N4096常量 |
| vit_contract_blocked_fp8_frag | 8 | 搬运/打包，无动态K矩阵循环；未改 |
| vit_qkv_project_normalize_fused_f16compact_fp8_frag | 8 | 候选128：token数常量化；K1024本已固定 |
| vit_attention_fused_400_bytein | 8 | 候选64：按256/400/640实际token数常量化，保留fallback |
| vit_project_frag | 8 | 候选2：K1024/N1024常量 |
| decoder_project2x_h16w | 2 | 候选4：五种固定通道对，空间尺寸保留动态 |
| decoder_project2x_h16w_byteout | 3 | 候选4：五种固定通道对，空间尺寸保留动态 |
| mh_ffn_fused_c64_project_g128_qkv_bytein_fb | 1 | 通道模板/常量已固定 |
| c32_fast_ffn_attention_fused_half_chain_finish | 1 | 矩阵维度/循环界限已固定；不盲目重做全局展开 |
| c32_post_merge_head_half | 1 | 矩阵维度/循环界限已固定；不盲目重做全局展开 |
