# 全网栅栏作用域 / CU 模式（模块集切换版）

不改核名，改成多装几套模块：`prepare.py` 按 `hip/build-modules.ps1` 的配方重新生成 c32_fused_ffn_attention-packed、multihead_fused_attention、deep_fast-packed、multihead-fast-padded-wave-packed 四个模块的源码，pair1 把所有 `__builtin_amdgcn_fence(…,"workgroup")` 限定为 LDS 地址空间，pair2 再给 KERNEL 宏加 `target("cumode")`。pair3 在机器上拼装：C32 取 pair2、其余三个取 pair1。

host 从 c32-pair-encode 的隔离 host 派生：多加载 `modules/pair<n>/` 下四个模块到 `<module>_pair<n>`，`Route()` 按槽把 c32_fused_ffn / mh_fused / deep_fast / mh_fast 的 launch 改到选中的集合，每帧计数 218 次并校验不变；原始 FP32 逐槽核对。`build.ps1` 复制 selected-modules 底包，双架构编译（gfx1200 放 `gfx1200-pair<n>`，gfx1201 进 `modules/pair<n>`）。`run.ps1` 两档整网 ABBA，每测试 8 槽。

结果：[fence-scope-all-20260922](../../../results/fence-scope-all-20260922/README.md)。
