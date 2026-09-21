# PR #5 review

PR: https://github.com/lmxxf/dlss5-on-amd-9070xt-porting/pull/5
Head: 4d14a32c102ba3e432f7984e7cadbf5224e45736
Base of two commits: 70656f8ec1cd1019ef537f17d557cc4a46365b09

结论：可采用分阶段bridge/可选噪声/动态codec参数的方向，不能原样合并。没有发布评论、合并或部署。

## 已验证的阻断项

1. **P1，bridge删除仍被调用的公开字段，现有HIP入口编译失败。** head的Development/HIP/hip_d3d12_bridge.h public区删除architecture/adapter_name/module_directory/device_match/runtime_version，而同一head的src/native_hip_network.h:76 LogDevice继续访问五者。MinGW C++17头文件最小编译基线通过、head报五项成员缺失。保留这些字段及初始化，不要求调用方丢失诊断功能。
2. **P1，删除架构子目录解析，现有双架构整包将找不到模块。** bridge Create的原架构验证/路径选择被删除，head约43～52行直接构建Network。默认调用方传assets/HIP，发布脚本放HIP/gfx1200和HIP/gfx1201；Network/Api.LoadModule直接打开指定路径，不会自行查子目录。修复编译后仍会尝试HIP/c32_prefix_reference.hsaco等不存在路径。应保留基于真实HIP属性的架构识别和子目录选择，允许外部已指定叶子目录的用法。
3. **P2，删除DLSS5_STRENGTH读取，旧调用方静默回到1,1。** src/native_game_codec.h:114～119新增参数有默认1，旧Record调用全部继续省略参数，但原环境配置读取已移除；用户包内README仍承诺该设置。支持每帧覆盖应同时保留旧调用签名/环境默认语义，并验证范围与非有限值。
4. **P2，codec失去自包含的必要声明。** 删除native_game_rgb_input.h间接包含后，独立包含native_game_codec.h的基线编译通过、head报CompileNativeShader未声明。应显式包含其声明所属头文件，不能依赖外部恰好先include别的头。

## 其他需调整的实现细节

- 原版已有基于typed HIP属性的LUID匹配。去掉会被Fake NVAPI伪装的VendorId硬门槛有用，但没有必要改成8192字节缓冲+272硬偏移。Api已经强制载入hipGetDevicePropertiesR0600，因此新代码在该导出不存在时才走name fallback的分支，在正常构造成功后基本不可达。LUID存在但不匹配时，不应仅因HIP count==1就盲选0；单HIP卡不代表游戏的D3D设备就是它。
- 新EnqueueAfterProducer约80～88行没有沿用Run的catch设置failed=true。部分排队失败后不应让同一个桥继续接受下一帧。还应写清Record/Submit/Signal/Wait/消费的顺序和帧串行化契约。
- SetNoise fast_prefix允许空vector的方向合理：50,331,648 float为201,326,592字节（192MiB）。这使新调用方可避免CPU分配；原本GPU路径已经不上传噪声，现有调用方若仍先构造vector，不会自动省下那份CPU内存。
- 动态参数、着色器编译错误文本都有价值。删除全部codec_step诊断日志与核心功能无关，宜保留可开关诊断。

## 与RE9/全屏的关系

PR只有四个bridge/network/codec/shader文件，没有改RE9回调、命令列表接入点、输入分辨率限制或全屏/交换链逻辑。作者描述是在燕云的外部接入里跑通，并认为可用于RE9/鬼武者；不能改写成RE9已验证。

我们RE9的既有证据是NGX出口之后，同一游戏命令列表还有51～53条后续draw/dispatch。拆接口为外部接入提供了构件，但queue级HIP往返仍需正确的提交边界，不能自动插入一条尚未提交命令列表的中间。Present后处理路线及≤1080输入契约不会因合并本PR自行改变。若目标是2K/4K输出下仍处理较低渲染分辨率，需要真正接到超分前，并在RE9实测。

## 验证方式与范围

git archive分别提取base/head的src、Development/HIP、shaders到/tmp/dlss5-pr5-review，未切换当前开发分支。两份最小TU分别只include src/native_hip_network.h和src/native_game_codec.h。

编译器x86_64-w64-mingw32-g++，-std=c++17 -D_WIN32_WINNT=0x0A00 -fsyntax-only；HIP TU额外-D DLSS5_USE_HIP、-D NATIVE_GAME_TILED_VERIFICATION（实际命令使用无空格的-DNAME写法）。两个base均通过（空日志），两个head分别出现上述错误。这里是C++兼容性检查，不是完整DLL链接、着色器运行或游戏实测。

建议先保留原有架构/诊断/配置契约，再增量引入三个接口；同步说明异常处理和提交顺序，然后用实际调用方演示同帧链路。RE9支持单独验收。
