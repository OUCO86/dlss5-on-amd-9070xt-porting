# 发布配置来源

正式新包的DLSS5-AMD/native-game-flags.txt来自本目录的版本控制模板：

| 版本 | 默认模板 |
|---|---|
| 普通OptiScaler游戏版 | hip-game-flags.txt |
| Magpie版 | hip-magpie-flags.txt |
| RE9特殊REFramework版 | hip-re9-flags.txt |

改默认值就改相应模板，再打包。普通游戏与RE9模板以2026-09-20已测试配置校对，移除机器专属gain路径；自适应默认0、FPS默认1。Magpie保留独立色彩/历史设置并补齐当前HIP优化参数。游戏内用户修改不反向改变模板。

正式入口Development/tools/optiscaler-stellarblade.ps1 -Action Release、package-magpie-candidate.ps1、RE9/package-0261.ps1直接复制模板，不从旧包/运行游戏继承flags再追加。其他文件仍可使用已校验基础包。package-026.ps1向两个子脚本传递ConfigDirectory。按仓库目录运行时默认定位scripts；若单独上传脚本到Windows，须同步模板并显式传入例如 -ConfigDirectory D:\DLSSNR-Lab\release-config。缺模板报错，不回退。不要只更新远端脚本、遗漏同提交的模板。

Release生成新包使用模板；Repack/FinalizeOnly仅重封已有stage，保留stage内配置。部署升级继续允许保留玩家现有设置，不因重新编译自动覆盖游戏。

Development/native-game-flags.txt是早期测试配置，scripts/game-flags.txt与magpie-flags.txt属旧DX12路线；不作为当前HIP正式发布默认值。

0.27三包统一入口：Development/tools/package-027.ps1，同样通过ConfigDirectory读取本目录模板。普通包从已校验的历史ZIP重新解压，不使用可能被运行过的解压目录；REFramework以已校验0.26.1完整包为底座。
