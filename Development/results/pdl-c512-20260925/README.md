# C512 链接旗子：单独有效，叠在 C64/128/256 上不加分（2026-09-25，Hikari）

`HIP/experiments/pdl-c512`：把 pdl-chain 那套 tile 旗子搬到 C512 链（块 23～30、40～47，每块 7 个 launch：mh_shift_pack、split_mix_blocked_h16w、split_ffn_fused_fp8_t8、split_projection_frag、mh_qkv_normalize_frag_c512、mh_attention_fused_fp8_out、mh_attention_project_frag_c512）。统一 tile = 16 个连续格子 token；各级等上一级同 tile（注意力等窗口的 8 个行段、shift_pack 按图像坐标等上一格子的 tile），每 wave 发计数器；每 tile 贡献：shift 256、mix 8、ffn 32、proj 8、qkv 24、attn 128、aproj 8。四个模块（deep_fast、mh_fast、mh_fused、mh reference）各加孪生，host 逐级传旗子。逐位：所有槽 0 差。

| ms/帧（A/B 相邻槽差） | 900 | 1080 |
|---|---|---|
| 只 C64/128/256（prod8 现状） | −0.19 / −0.18 | −0.12 |
| 只 C512 | −0.16 | −0.11 |
| 两者都开 | −0.16 / −0.15 | −0.09 |

不相加。板功耗钉在 325～328 W（clock-ledger），把哪一族的空隙填上，省下的时间都以时钟回吐——两族单独各回收 ~0.15 ms，像是同一份"时钟预算"，不是各自的空隙账。**不采用 C512 部分**（四个模块多一套代码换零收益）。用户侧：Adrenalin 功耗上限 +10% 后两者可能相加，值得实机复测一次（`run.ps1 -Heights 900 -Table 0,15,7 -Tests 2`）。

坑：实验 host 从生产头文件打补丁，生产 ctor 只在 `opt.pdl` 时分配旗子缓冲，而 timeline 的 flags.txt 没写 `DLSS5_HIP_PDL=1`，C512 模式对着空指针算偏移直接 launch 失败——实验 host 改为无条件分配。
