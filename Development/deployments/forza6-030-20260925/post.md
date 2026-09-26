DLSS5@AMD 0.30 简介（顺带《极限竞速：地平线 6》实测）

0.30 三个包（Magpie / OptiScaler / OptiScaler-REFramework）都已上传：
夸克 https://pan.quark.cn/s/80a735ab9f88
Google Drive https://drive.google.com/drive/folders/1pKZpLosgJXxUOZTMg_m0sbCipX9Q3WYo?usp=sharing

0.24 到 0.30 改了什么（一句话版）：
- 0.24：前置路线上线。低分辨率颜色先过 DLSS5 再交给 OptiScaler 的 FSR 放大，剑星 2K 质量档约 35 帧。
- 0.25 / 0.26：内核第一轮优化（FP8 字节直传、权重预排），新增 9060 系列 gfx1200 内核，修中文路径、900 档尾部漏写、匹诺曹黑屏。
- 0.26.1 / 0.28.1：RE9 专用的 REFramework 包（后置接入），普通游戏别用这个。
- 0.27 / 0.28：流式 ViT 注意力、六项逐位无损核优化，帧率小幅上涨、画面不变。
- 0.29：输入不再限制 1080P，超过的缩到 1080 档跑再还原（2K Native AA 可用）；核累计再快约 7%，剑星 900P 约 60 帧。发布起同时传 Google Drive。
- 0.30：同一条流上 launch 任意序 + tile 旗子（土法 programmatic dependent launch），逐位无损再快 1～2%；2077 零配置（同步提交 + 只转亮度，修绿色霓虹变褐）；修好切档位后神经处理消失的 bug。

《极限竞速：地平线 6》（Xbox 商店版）：
装 0.30 的 OptiScaler 常规包能进游戏，但默认配置下 F6 没反应、画面没变化——原因是这游戏在同一条命令列表里 FSR 之后还有自己的绘制，前置路线第一帧判定不安全就自动放弃，之后全部透传，表现为"装了跟没装一样"。
解法一行：打开游戏目录里 DLSS5-AMD\native-game-flags.txt，把
DLSS5_PRE_UPSCALE=1
改成
DLSS5_PRE_UPSCALE=0
重启游戏，走后置路线。9070 XT 实测 2K 质量档（渲染 1508×848）约 44 帧，F6 开关有效，方向盘/手部细节能看出变化。黄字帧率不显示，不影响处理。
下个版本改成自动探测，不用手动改。
