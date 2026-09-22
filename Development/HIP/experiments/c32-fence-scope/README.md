# C32 栅栏作用域 / CU 模式

只换 `sync_window()` / `sync_owned_rows()` 的实现，barrier、矩阵顺序、LDS 布局不动。`prepare.py` 从生产源切出融合体，生成三个 `_pairN` 变体（1 = LDS 地址空间栅栏；2 = CU 模式；3 = 两者），写到 `/tmp/c32-fence-scope/kernel.hip`。

复用 c32-pair-encode 的 `network.exe`（按槽给 c32_fused_ffn 模块的核名加 `_pair<mode>`），所以不用重编 host。`build.ps1` 用 network-fixed-shapes/selected-modules 底包只替换 C32 模块，双架构编译；`run.ps1` 两档整网 ABBA，每槽校验原始 FP32 与替换数。

结果：[c32-fence-scope-20260922](../../../results/c32-fence-scope-20260922/README.md)。
