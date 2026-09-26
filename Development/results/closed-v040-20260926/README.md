# 闭源 v0.4.0 二进制调查：寄存器驻留、大块融合与默认光色控制

2026-09-26，Yami。用户给出 `C:\Users\lmxxf\Downloads\dlssnr_on_amd_setup.exe`，要求看新版用了什么优化；随后补充网友截图偏淡、灯光和浓郁色彩感较弱。

## 样本与方法

- 本地样本13,183,488字节，SHA256 `2d37453e918a1c5487314b3ae7c088b624ac0be1b82469427ec04b481a845ded`，与GitHub API的 **v0.4.0资产digest完全一致**。
- 下载官方v0.3.3作为对照：10,763,776字节，SHA256 `af5b9bbe8e97eea4c564341a78caf752de02a0b622a141c53c5a70e782fec994`，也与发布资产digest一致。
- 静态提取内嵌PE DLL和Clang offload bundle，未执行安装器、未装游戏、未运行闭源核。两版各含8个GPU code object和空host bundle条目。
- 用本机libLLVM20的AMDGPU反汇编接口读gfx1201，v0.3.3共44个函数，v0.4.0共86个，**全部解码成功、未知指令0**。读取ELF MsgPack元数据，再对照宿主x86汇编。
- 官网缓存页面当时还显示v0.3.3；实际API返回v0.4.0（2026-09-25 17:24:10 UTC发布），说明写“比v0.3.3性能提升42%”。版本判断以资产hash为准。[官方v0.4.0发布](https://github.com/danielblnc/DLSS-NR-on-AMD/releases/tag/v0.4.0)

这是静态调查，尚未捕获真实游戏的核调用轨迹或做同条件帧率对比，不能把作者42%或网友60fps当我们的实测。

## 这次新增了什么

新增42个导出，无删除：24个 `k_reg_swin_mh<C,mode>`（C64/C128/C256），7个reg1d，7个reg_vit，2个512布局转换，1个C256跨层chain，1个clock probe。

**C32单wave快核在v0.3.3已经存在**，不能把它说成v0.4.0刚发明。此次更显眼的是将寄存器路线扩到多头Swin和ViT/C512；与速度增幅的因果份额仍需运行时测量。

### 02:21后追到的明确切换点

用户指出应找让性能阶跃的关键改法，不能把新增导出当成许多独立小优化。继续对齐宿主派发得到：

- **0.3.3，CPU VA `0x1800363a3`**：先检查通道是否等于32，再检查register flag；只有C32进入寄存器快核。其余进入通用Swin路径。
- **0.4.0，`0x180039c67`**：同类register flag后改成通道跳转表，C32/C64/C128/C256均走快路径。表在`0x18007a480`，目标地址已解码到`dispatch-delta.json`。
- register开关的缺省开启条件两版已有（gfx12、NO_REG/SLOW_PREPOST未设置）；并非单纯把原来的默认0改成1。关键是**同一快路径覆盖范围扩大，并有新核支撑**。
- 通用路径按窗口分配显式global workspace：C32/C64每窗口8KiB，C128为16KiB，C256为32KiB。新版快分支绕过这块分配；这个workspace与编译器private spill是两回事。
- 旧C64 GPU核一开始就从参数偏移`0xa0`读workspace指针（GPU VA `0x95a04`），加上窗口编号×8192，随后`0x95c7c`向它执行global_store_b32。准备后的输入特征至少会写进这块空间；不能未经完整数据流就把整块仅命名为“注意力概率表”。
- 旧C64静态有global_store_b8 35条、global_store_b32 3条；新reg C64只有global_store_b128 4条（另有scratch spill）。这是结构证据，不将静态条数相加当动态流量。

**旧swin_var也已经是融合核。** 因此此次关键候选不是“首次融合”，而是把原来融合核里的中间状态改为寄存器/片上协作，并让一个wave承担一个head的完整窗口。24个MH导出是3种通道×8种模式，可由一个组织原则展开，不代表24项独立优化。

与我们旧实验也对上了：`Development/HIP/c64_window_fused.hip` 明确256线程，attention中`head=alltid/128`、`first=awave*16`，仍是一个head四wave，并在LDS保存nrm/feat；“整窗融合试过没赚”没有测到这次的一头一wave结构。当前证据已把关键候选收窄，但还不能声称42%全部由它贡献，也不能承诺我们一改就得到同样幅度。

代表性资源（线程栏为元数据声明上限；C32/C64已在宿主launch代码确认实际发32/64线程）：

| 核 | 线程 | LDS | VGPR | private bytes/thread | 静态barrier |
|---|---:|---:|---:|---:|---:|
| v0.3.3 reg_swin32<0> | 32 | 2048B | 168 | 40 | 0 |
| v0.4.0 reg_swin32<0> | 32 | 2048B | 168 | 56 | 0 |
| v0.3.3 swin_var<64,false> | 256 | 15616B | 119 | 24 | 17 |
| v0.4.0 reg_swin_mh<64,0> | 64 | 4096B | 168 | 144 | 7 |
| v0.4.0 reg_swin_mh<128,0> | 128 | 8192B | 168 | 144 | 7 |
| v0.4.0 reg_swin_mh<256,0> | 256 | 32768B | 168 | 64 | 7 |
| v0.4.0 reg_vit_ffwd<1,false> | 32 | 0 | 96 | 0 | 0 |

不能把所有private字节都称为溢出，但C32和新MH也有明确的vgpr_spill_count及scratch_load/store，确实付了溢出代价。C256的LDS没有随这次路线缩小；不要只挑好看的资源数据。

## 值得借的机制

### 1. 一wave掌握完整窗口/一个头，减少跨wave交换

`k_reg_swin32<0>`入口按group x/y乘8定位，四次global_load_b128载入、尾部四次global_store_b128写回；32线程，0个barrier，LDS仅2KB。我们的C32是128线程/4wave，每wave16 token，LDS15360B，阶段间需协作。

新MH的组规模随头数增长：C64两wave、C128四wave、C256八wave，匹配每head32维、一wave承载该头窗口的组织。FFN/QKV/归一化/注意力/投影的大块代码在同一导出内，减少中间张量下落和launch边界；跨头混合仍需要LDS与同步。

这比只改工作组编号更大：它改变的是哪些数据由同一个wave持有。声明上限、访存与指令结构支持这个判断，但每块在具体游戏中是否选中仍待动态确认。

### 2. 激活按4×4小块/片段组织，配合宽读写

C32入口地址计算有坐标除4、块地址乘512、lane地址乘16；32通道FP8的4×4块恰为512B。一个8×8窗口从四个小块各读一条128位/lane，输出同样四次宽写。4像素移位因此对应小块边界，避免把每个像素逐个捡进LDS。

这是从寻址公式推导的布局，需要复现时再完整确认lane/通道排列；不能只按“4×4”写个猜测版本。模块还有tin_to_frag/frag_to_tin及新增512版本，明确存在片段布局转换路径。

### 3. 成对半精度算术与wave内归约

可见大量 `v_pk_mul_f16`、`v_pk_add_f16`、`v_fma_mixlo/hi_f16`，结合 `ds_bpermute_b32`、`v_perm_b32` 做寄存器内组织和归约；C32 reg主核的WMMA均为FP8，没有我们用于部分求和的FP16 WMMA。

例：C32 mode0在GPU VA `0x5a37c..0x5a574`，packed half平方/加法、跨lane交换、转f32与rsqrt相邻出现。这是具体算术路线差异，**尚未证明与我们/原版逐位等价**。学它的存储与协作组织时，不能顺手照搬求和树或控制参数。

### 4. 跨层chain有实现，但默认不能算进收益

新增 `k_reg_swin_chain<256>`，并有按层循环/旗子等待相关代码和诊断。宿主 `0x1800347cd` 查询 `DLSSNR_CHAIN`，存在才置位；普通缺省不启用。因此“v0.4.0有chain”不等于作者默认42%来自chain。

## 偏淡：发现了直接对应的默认配置

安装包在文件偏移约`0xbf09df`附近嵌入完整INI模板，已提取为 `default.ini`：

```ini
LocalTone=0
LocalStructure=1
SkinStructure=-1
Style=0
ToneChannels=0
ToneCurve=reinhard
ToneLift=0
UseGameExposure=1
PreUpscale=1
```

UI把LocalTone说明为“大范围光照与色彩响应（DLSSNR.LocalToneStrength）”。宿主配置读取 `0x18000865e..0x18000868e` 确认LocalTone缺省0；`0x18001bea7..0x18001bf0e` 将它放进本帧控制参数，ToneChannels=0还使另一控制分量为0，结构/自动皮肤分量则为1。默认用于dump的四个控制值因此是0/0/1/1。

**若网友沿用默认，这与“结构有变化、光照和色彩响应偏淡”相符，值得优先检查LocalTone，而不是先归罪于提速算法。** 但没拿到网友实际INI，也没有同帧LocalTone 0/1对照，所以只是有具体证据的解释候选，不是已复现的根因。ToneLift默认0，不能把抬黑位当成既定原因。

这些控制改变网络工作点/色彩处理，不自动减少网络层数；没有证据据此说它用“关闭灯光计算”换FPS。借性能架构时保留我们当前的视觉参数和数值合同。

## 1080P 60fps的口径

INI模板与宿主读取都确认PreUpscale默认1。DLL日志文本也明确：网络在render-resolution colour上运行，校正结果再交给FSR。若游戏输出1080P但使用超分，网络计算尺寸可以低于1080P。另有FG、提交/跳过计数与network GPU ms日志，可用于后续同条件核对。

因此60fps尚未核实；也没有证据否定它。要比较的是网络输入/处理尺寸、是否FG、每帧是否实际跑网络以及同场景帧时。

## 对本项目的下一步

02:21后的优先级收窄为：先围绕**C64一头一wave**做独立受控原型，比较它与我们旧256线程整窗融合、现行两段流水的差别，核实中间状态真正留在哪里。先保持现有舍入/归约/控制值，不同时动色调、分辨率、跳层。C32可作为实现热身，但它不是v0.4.0新增，不能用它解释这次42%的版本增幅。

当前C32权重片段预排仍有价值，但它只是较小的布局试验；此次证据表明“每个窗口必须四wave共享LDS”是实现选择，不能列成算法必付成本。

## 文件与复现

- `extraction-040.json` / `extraction-033.json`、`release-sources.json`：样本与发布身份。
- `kernels-040.json` / `kernels-033.json`、`kernel-resources.csv`、`comparison.json`：全部导出、资源、静态指令计数、代码hash与版本差异。
- `host-evidence.txt`：关键CPU汇编地址摘录；`default.ini`：安装模板。
- 脚本 `Development/tools/closed-inspect/{extract,disassemble,compare}.py`。disassemble需msgpack与支持gfx1201的libLLVM20，可显式传库路径。
- 二进制、完整CPU/GPU反汇编仅留 `/tmp/dlssnr-closed-20260926`，未放进公开源码树。复算：extract.py 安装包 输出目录；disassemble.py 输出目录 libLLVM路径；compare.py 两版kernels.json。
