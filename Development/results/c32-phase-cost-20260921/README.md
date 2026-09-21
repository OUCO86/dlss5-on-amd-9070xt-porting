# C32阶段实验归档索引

本批已完成，按用户要求保留逐项报告，暂不作总体汇总或性能排名。

- 七个主阶段，900/1080 ×入口/链/末端，共504个测量槽位。
- 整组寄存器编码探针补充校准72槽位。
- 全部576槽位产出缓冲逐byte一致；24次首尾整网原始FP32一致。
- gfx1200/gfx1201均编译，实际GPU运行仅gfx1201；无游戏部署/生产改动。

- [ffn](reports/ffn.md)
- [pack](reports/pack.md)
- [packv](reports/packv.md)
- [qkv](reports/qkv.md)
- [scores](reports/scores.md)
- [norm](reports/norm.md)
- [av](reports/av.md)
- [project](reports/project.md)

初版报告/数据：initial-900-post、unroll-control-900-post及initial-isa.json。初版norm因外层QKV不再展开而出现较大扰动，显式unroll3后恢复结构；逐标量pack探针仍有明显扰动，去掉全memory clobber未解决，packv仅减轻，不能假装无扰动。

主模型输入、参数、算法、精度与舍入顺序保持原状。矩阵重复结果通过opaque消费保留，编码重复用opaque寄存器观察保留；数据/依赖所致的探针局限在每份报告里单独注明。输入暂存、最后finish/RGB等未重复区域，以及真实GEMM台阶实验，不在本批的已完成范围。
