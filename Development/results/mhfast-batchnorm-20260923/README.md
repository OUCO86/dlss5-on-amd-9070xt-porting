# ffn_fused_c256 的 barrier 审查与 BatchNorm=true 试验（2026-09-23，Hikari）

打点账里 barrier 等待占 19%（每 wave 8 次）。逐个审依赖（ByteIn 路径）：hidden 写→收缩读、hidden 复用（收缩读完→投影特征写）、投影特征写→读、qfeature 写→QKV 读，这四个是真依赖；QKV 归一化 part 0/1 各一对（raw 写→算 inverse→读）共四个。函数体已有 `BatchNorm=true` 分支把两个 part 合成一对，生产实例用的是 false。

变体：该核名的模板参数 BatchNorm 翻为 true，其余不变。逐位同。ISA：barrier 8→6，指令 2237→2057，但 storage.raw 需容纳两个 part，LDS 21.6→39.0KB，编译器驻留 12→10，VGPR 102→127。

整网 ABBA 三份：1080 −0.023/−0.003/+0.001ms，900 −0.004/−0.002/−0.011，全部交叠。**省两个 barrier 被 LDS 翻倍抵消**，不采用。结论：这个核剩下的 barrier 都是真依赖，不动数据流拿不掉；同步等待 19% 是结构税。

证据：r1/。工具 HIP/experiments/mhfast-batchnorm。
