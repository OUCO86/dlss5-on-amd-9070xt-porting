# C32 输入/尾部归档

本批完成 900/1080 × prefix/chain/post；120 个计时槽完整产出比较、12 次原始网络 FP32 检查均逐位相同。双架构编译，运行仅 gfx1201。

- [输入](input.md)：读取、映射、合并、暂存及 prefix 前置投影。
- [尾部](tail.md)：finish/main8/下采样和 RGB 头。
- summary.json、isa.json、artifacts.json 与六个目录保留原始证据。

按用户要求分别存档，暂不跨批次汇总。没有生产代码变更。
